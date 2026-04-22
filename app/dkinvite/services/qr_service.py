from pathlib import Path

import qrcode
from flask import current_app

class QrService:
    @staticmethod
    def _static_root() -> Path:
        return Path(current_app.root_path).parent / "static"

    @staticmethod
    def _qrs_dir() -> Path:
        qrs_dir = QrService._static_root() / "qrs"
        qrs_dir.mkdir(parents=True, exist_ok=True)
        return qrs_dir

    @staticmethod
    def build_ticket_url(ticket_id: str) -> str:
        base = current_app.config["PUBLIC_BASE_URL"].rstrip("/")
        return f"{base}/ticket/{ticket_id}"

    @staticmethod
    def generate_for_ticket(ticket_id: str) -> str:
        file_name = f"{ticket_id}.png"
        output_path = QrService._qrs_dir() / file_name

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(QrService.build_ticket_url(ticket_id))
        qr.make(fit=True)

        image = qr.make_image(fill_color="black", back_color="white")
        image.save(output_path)

        return f"qrs/{file_name}"

    @staticmethod
    def delete_for_ticket(ticket_id: str) -> None:
        path = QrService._qrs_dir() / f"{ticket_id}.png"
        if path.exists():
            path.unlink()
