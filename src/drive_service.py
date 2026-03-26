from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import time

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials

from src.config import Settings

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveAccessError(RuntimeError):
    pass


@dataclass(slots=True)
class DriveFile:
    file_id: str
    name: str
    mime_type: str


class GoogleDriveService:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self._token_cache: str | None = None
        self._token_expiry_epoch: float = 0.0
        self._folders_cache_path = self.settings.history_dir / "drive_folders_cache.json"
        self._http = requests.Session()

    def is_configured(self) -> bool:
        return bool(
            self.settings.google_service_account_file
            or self.settings.google_oauth_user_file
            or self.settings.google_clasp_profile
        )

    def get_sheet_metadata(self, sheet_id: str) -> dict:
        return self._request(
            "GET",
            f"https://www.googleapis.com/drive/v3/files/{sheet_id}",
            params={"fields": "id,name,mimeType,parents,capabilities,ownedByMe"},
        )

    def resolve_sheet_parent_folder(self, sheet_id: str) -> str:
        metadata = self.get_sheet_metadata(sheet_id)
        parents = metadata.get("parents") or []
        if not parents:
            raise DriveAccessError(
                "La sheet no tiene carpeta padre resoluble por API."
            )
        return str(parents[0])

    def find_folder_by_name(self, parent_id: str, folder_name: str) -> DriveFile | None:
        safe_name = folder_name.replace("'", "\\'")
        query = (
            f"mimeType='{FOLDER_MIME}' and trashed=false and "
            f"name='{safe_name}' and '{parent_id}' in parents"
        )
        result = self._request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            params={"q": query, "fields": "files(id,name,mimeType)"},
        )
        files = result.get("files") or []
        if not files:
            return None
        file = files[0]
        return DriveFile(
            file_id=str(file["id"]),
            name=str(file["name"]),
            mime_type=str(file["mimeType"]),
        )

    def create_folder(self, parent_id: str, folder_name: str) -> DriveFile:
        payload = {
            "name": folder_name,
            "mimeType": FOLDER_MIME,
            "parents": [parent_id],
        }
        created = self._request(
            "POST",
            "https://www.googleapis.com/drive/v3/files",
            json_payload=payload,
            params={"fields": "id,name,mimeType"},
        )
        return DriveFile(
            file_id=str(created["id"]),
            name=str(created["name"]),
            mime_type=str(created["mimeType"]),
        )

    def ensure_folder(self, parent_id: str, folder_name: str) -> DriveFile:
        existing = self.find_folder_by_name(parent_id, folder_name)
        if existing:
            return existing
        self.logger.info("Creando carpeta Drive '%s' bajo parent %s", folder_name, parent_id)
        return self.create_folder(parent_id, folder_name)

    def ensure_reports_structure(
        self, sheet_id: str, force_refresh: bool = False
    ) -> dict[str, str]:
        if not force_refresh:
            cached = self._load_cached_folder_ids(sheet_id)
            if cached:
                self.logger.info(
                    "Usando cache de carpetas Drive para sheet %s.", sheet_id
                )
                return cached

        parent_id = self.resolve_sheet_parent_folder(sheet_id)
        informes = self.ensure_folder(parent_id, self.settings.drive_reports_root)
        semanal = self.ensure_folder(informes.file_id, self.settings.drive_weekly_folder)
        mensual = self.ensure_folder(informes.file_id, self.settings.drive_monthly_folder)
        anual = self.ensure_folder(informes.file_id, self.settings.drive_annual_folder)
        folder_ids = {
            "sheet_parent_id": parent_id,
            "informes_id": informes.file_id,
            "weekly_id": semanal.file_id,
            "monthly_id": mensual.file_id,
            "annual_id": anual.file_id,
        }
        self._save_cached_folder_ids(sheet_id, folder_ids)
        return folder_ids

    def find_pdf_by_name(self, parent_id: str, file_name: str) -> DriveFile | None:
        safe_name = file_name.replace("'", "\\'")
        query = (
            "mimeType='application/pdf' and trashed=false and "
            f"name='{safe_name}' and '{parent_id}' in parents"
        )
        result = self._request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            params={"q": query, "fields": "files(id,name,mimeType)"},
        )
        files = result.get("files") or []
        if not files:
            return None
        file = files[0]
        return DriveFile(
            file_id=str(file["id"]),
            name=str(file["name"]),
            mime_type=str(file["mimeType"]),
        )

    def upload_pdf(self, parent_id: str, local_file_path: Path, drive_name: str) -> DriveFile:
        metadata = {"name": drive_name, "parents": [parent_id]}
        with local_file_path.open("rb") as file_handle:
            response = self._http.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType",
                headers={"Authorization": f"Bearer {self._get_token()}"},
                files={
                    "metadata": (
                        "metadata",
                        json.dumps(metadata),
                        "application/json; charset=UTF-8",
                    ),
                    "file": (drive_name, file_handle, "application/pdf"),
                },
                timeout=60,
            )
        if response.status_code >= 400:
            raise DriveAccessError(
                f"Upload PDF fallo ({response.status_code}): {response.text}"
            )
        payload = response.json()
        return DriveFile(
            file_id=str(payload["id"]),
            name=str(payload["name"]),
            mime_type=str(payload["mimeType"]),
        )

    def _request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_payload: dict | None = None,
    ) -> dict:
        token = self._get_token()
        response = self._http.request(
            method,
            url,
            params=params,
            json=json_payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        if response.status_code >= 400:
            raise DriveAccessError(
                f"Drive API error {response.status_code}: {response.text}"
            )
        if not response.content:
            return {}
        return response.json()

    def _get_token(self) -> str:
        now = time.time()
        if self._token_cache and now < self._token_expiry_epoch - 30:
            return self._token_cache

        if self.settings.google_service_account_file:
            token = self._token_from_service_account(
                Path(self.settings.google_service_account_file)
            )
            self._token_cache = token
            self._token_expiry_epoch = now + 3300
            return token

        if self.settings.google_oauth_user_file:
            token = self._token_from_oauth_user(Path(self.settings.google_oauth_user_file))
            self._token_cache = token
            self._token_expiry_epoch = now + 3300
            return token

        if self.settings.google_clasp_profile:
            token, expires_in = self._token_from_clasp_profile()
            self._token_cache = token
            self._token_expiry_epoch = now + int(expires_in)
            return token

        raise DriveAccessError("No hay credenciales Google configuradas para Drive API.")

    def _token_from_service_account(self, path: Path) -> str:
        if not path.exists():
            raise DriveAccessError(f"No existe service account file: {path}")
        creds = service_account.Credentials.from_service_account_file(
            str(path), scopes=[DRIVE_SCOPE]
        )
        creds.refresh(GoogleRequest())
        return str(creds.token)

    def _token_from_oauth_user(self, path: Path) -> str:
        if not path.exists():
            raise DriveAccessError(f"No existe OAuth user file: {path}")
        creds = UserCredentials.from_authorized_user_file(str(path), scopes=[DRIVE_SCOPE])
        creds.refresh(GoogleRequest())
        return str(creds.token)

    def _token_from_clasp_profile(self) -> tuple[str, int]:
        clasp_file = (
            Path(self.settings.google_clasp_file).expanduser()
            if self.settings.google_clasp_file
            else Path.home() / ".clasprc.json"
        )
        if not clasp_file.exists():
            raise DriveAccessError(f"No existe .clasprc: {clasp_file}")
        payload = json.loads(clasp_file.read_text(encoding="utf-8"))
        token_obj = (payload.get("tokens") or {}).get(self.settings.google_clasp_profile)
        if not token_obj:
            raise DriveAccessError(
                f"No existe perfil '{self.settings.google_clasp_profile}' en {clasp_file}."
            )
        response = self._http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": token_obj["client_id"],
                "client_secret": token_obj["client_secret"],
                "refresh_token": token_obj["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise DriveAccessError(
                f"Refresh token .clasprc fallo ({response.status_code}): {response.text}"
            )
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise DriveAccessError("No se obtuvo access_token desde .clasprc.")
        expires_in = int(data.get("expires_in", 3600))
        return token, expires_in

    def _load_cached_folder_ids(self, sheet_id: str) -> dict[str, str] | None:
        if not self._folders_cache_path.exists():
            return None
        try:
            payload = json.loads(self._folders_cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            entry = payload.get(sheet_id)
            if not isinstance(entry, dict):
                return None
            required = {
                "sheet_parent_id",
                "informes_id",
                "weekly_id",
                "monthly_id",
                "annual_id",
            }
            if not required.issubset(set(entry.keys())):
                return None
            return {key: str(entry[key]) for key in required}
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return None

    def _save_cached_folder_ids(self, sheet_id: str, folder_ids: dict[str, str]) -> None:
        payload: dict[str, dict] = {}
        if self._folders_cache_path.exists():
            try:
                raw = json.loads(self._folders_cache_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw
            except (json.JSONDecodeError, OSError):
                payload = {}
        payload[sheet_id] = {
            **folder_ids,
            "updated_at_epoch": int(time.time()),
        }
        self._folders_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._folders_cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
