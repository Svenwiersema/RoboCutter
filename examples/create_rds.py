from robocutter.documents import RoboDocument

doc=RoboDocument(
    title="RoboCutter Documentation Standard",
    code="RC-RDS-001"
)
doc.add_cover()
doc.add_heading("Inleiding")
doc.add_paragraph("Eerste officiële RoboDocument v1.0 document.")
doc.save("RC-RDS-001.docx")
