from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(slots=True)
class Settings:
    project_visible_name: str
    project_slug: str
    company_name: str
    author_name: str
    timezone_name: str

    google_sheet_id: str
    use_public_sheet_export: bool

    google_service_account_file: str | None
    google_oauth_user_file: str | None
    google_clasp_profile: str | None
    google_clasp_file: str | None

    logo_path: Path
    output_dir: Path
    history_dir: Path
    log_dir: Path

    drive_reports_root: str
    drive_weekly_folder: str
    drive_monthly_folder: str
    drive_annual_folder: str

    email_enabled: bool
    email_dry_run_default: bool
    email_provider: str
    email_from: str
    email_smtp_host: str | None
    email_smtp_port: int
    email_smtp_user: str | None
    email_smtp_password: str | None
    email_use_tls: bool
    email_require_confirmation: bool

    log_level: str

    # Identidad visual (Artes Buho)
    color_primary_red: str = "#C62828"
    color_primary_yellow: str = "#FFCA28"
    color_white: str = "#FFFFFF"
    color_text_dark: str = "#1E1E1E"

    @property
    def has_google_credentials(self) -> bool:
        return any(
            [
                self.google_service_account_file,
                self.google_oauth_user_file,
                self.google_clasp_profile,
            ]
        )

    @property
    def reports_local_root(self) -> Path:
        return self.output_dir / self.drive_reports_root


def load_settings() -> Settings:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    settings = Settings(
        project_visible_name=os.getenv("PROJECT_VISIBLE_NAME", "SITUACION BANDAS"),
        project_slug=os.getenv("PROJECT_SLUG", "SITUACION-BANDAS"),
        company_name=os.getenv("COMPANY_NAME", "Artes Buho"),
        author_name=os.getenv("AUTHOR_NAME", "RUBEN COTON"),
        timezone_name=os.getenv("TIMEZONE", "Europe/Madrid"),
        google_sheet_id=os.getenv(
            "GOOGLE_SHEET_ID", "1YUOtxFLvryw_LmkoI2NB3FBeNucw0hFDdQa2qflr-xs"
        ),
        use_public_sheet_export=_as_bool(
            os.getenv("USE_PUBLIC_SHEET_EXPORT"), default=True
        ),
        google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or None,
        google_oauth_user_file=os.getenv("GOOGLE_OAUTH_USER_FILE") or None,
        google_clasp_profile=os.getenv("GOOGLE_CLASP_PROFILE") or None,
        google_clasp_file=os.getenv("GOOGLE_CLASP_FILE") or None,
        logo_path=PROJECT_ROOT / os.getenv("LOGO_PATH", "assets/logo_artes_buho.jpg"),
        output_dir=PROJECT_ROOT / os.getenv("OUTPUT_DIR", "data/outputs"),
        history_dir=PROJECT_ROOT / os.getenv("HISTORY_DIR", "data/history"),
        log_dir=PROJECT_ROOT / os.getenv("LOG_DIR", "data/logs"),
        drive_reports_root=os.getenv("DRIVE_REPORTS_ROOT", "Informes"),
        drive_weekly_folder=os.getenv("DRIVE_WEEKLY_FOLDER", "InformeSemanal"),
        drive_monthly_folder=os.getenv("DRIVE_MONTHLY_FOLDER", "InformeMensual"),
        drive_annual_folder=os.getenv("DRIVE_ANNUAL_FOLDER", "InformeAnual"),
        email_enabled=_as_bool(os.getenv("EMAIL_ENABLED"), default=False),
        email_dry_run_default=_as_bool(
            os.getenv("EMAIL_DRY_RUN_DEFAULT"), default=True
        ),
        email_provider=os.getenv("EMAIL_PROVIDER", "smtp"),
        email_from=os.getenv("EMAIL_FROM", "booking@artesbuhomanagement.com"),
        email_smtp_host=os.getenv("EMAIL_SMTP_HOST") or None,
        email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
        email_smtp_user=os.getenv("EMAIL_SMTP_USER") or None,
        email_smtp_password=os.getenv("EMAIL_SMTP_PASSWORD") or None,
        email_use_tls=_as_bool(os.getenv("EMAIL_USE_TLS"), default=True),
        email_require_confirmation=_as_bool(
            os.getenv("EMAIL_REQUIRE_CONFIRMATION"), default=True
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
    ensure_runtime_dirs(settings)
    return settings


def ensure_runtime_dirs(settings: Settings) -> None:
    for path in (
        settings.output_dir,
        settings.history_dir,
        settings.log_dir,
        settings.reports_local_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
