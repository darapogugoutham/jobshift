import io
import textwrap
from datetime import UTC, datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.models import AnonymousSession
from app.tasks.service import list_tasks, total_hours


def make_json_export(db: Session, owner: AnonymousSession) -> dict:
    tasks = list_tasks(db, owner)
    return {
        "session_id": str(owner.id),
        "input_revision": owner.input_revision,
        "exported_at": datetime.now(UTC).isoformat(),
        "total_hours": total_hours(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "task_description": t.task_description,
                "hours_per_week": t.hours_per_week,
                "frequency": t.frequency,
                "tools_used": t.tools_used,
                "skills_used": t.skills_used,
                "involves_people": t.involves_people,
                "physical_presence_required": t.physical_presence_required,
                "decision_authority": t.decision_authority,
                "notes": t.notes,
            }
            for t in tasks
        ],
        "analysis": {"status": "not_implemented", "result": None},
        "scenario": None,
        "plan": None,
        "metadata": {
            "application": "JobShift",
            "reference_data": "not_imported",
            "core_engines": "not_implemented",
        },
    }


def make_pdf_export(db: Session, owner: AnonymousSession) -> bytes:
    data = make_json_export(db, owner)
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    _width, height = letter
    y = height - 54
    pdf.setTitle("JobShift task inventory")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, y, "JobShift task inventory")
    y -= 28
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, y, f"Exported: {data['exported_at']}")
    y -= 16
    pdf.drawString(
        48,
        y,
        f"Input revision: {data['input_revision']} · Total: {data['total_hours']} hours per week",
    )
    y -= 28
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(48, y, "Analysis status: Not implemented")
    y -= 17
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        48, y, "The analysis engine is not connected. This report contains saved tasks only."
    )
    y -= 28
    for index, task in enumerate(data["tasks"], 1):
        lines = [
            f"{index}. {task['task_description']}",
            f"   {task['hours_per_week']} hours/week · Frequency: {task['frequency'] or 'not provided'}",
            f"   Tools: {', '.join(task['tools_used'] or []) or 'not provided'} · Skills: {', '.join(task['skills_used'] or []) or 'not provided'}",
        ]
        if task["notes"]:
            lines.append("   Notes: " + task["notes"])
        for line in lines:
            # ReportLab's built-in Helvetica font covers Windows-1252 only.
            printable = line.encode("cp1252", "replace").decode("cp1252")
            for wrapped in textwrap.wrap(printable, width=100) or [""]:
                if y < 55:
                    pdf.showPage()
                    y = height - 54
                pdf.setFont("Helvetica", 9)
                pdf.drawString(48, y, wrapped)
                y -= 14
        y -= 8
    pdf.showPage()
    pdf.save()
    return output.getvalue()
