"""Frontend pairs; canonical positives copied unchanged from locked C5 archive."""
from file_fixtures import PDF,PROTECTED_PDF,XLSX
import io,re,zipfile

def without_member(blob,member):
 out=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(blob))as source,zipfile.ZipFile(out,'w',zipfile.ZIP_STORED)as target:
  for entry in source.infolist():
   if entry.filename!=member:target.writestr(entry,source.read(entry))
 return out.getvalue()
def file_gate_cases():
 pdf='application/pdf';xlsx='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 return [('plain-pdf',PDF,pdf,'file','Pdf'),('protected-pdf',PROTECTED_PDF,pdf,'file','ProtectedPdf'),('old-invalid-pdf',b'%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\n%%EOF',pdf,'protocol',None),('bad-xref-pdf',re.sub(rb'startxref\n[0-9]+',b'startxref\n999999',PDF),pdf,'protocol',None),('canonical-xlsx',XLSX,xlsx,'file','Xlsx'),('missing-root-relationship',without_member(XLSX,'_rels/.rels'),xlsx,'protocol',None),('missing-worksheet',without_member(XLSX,'xl/worksheets/sheet1.xml'),xlsx,'protocol',None),('generic-zip-is-not-xlsx',b'PK\x05\x06'+bytes(18),xlsx,'protocol',None)]
