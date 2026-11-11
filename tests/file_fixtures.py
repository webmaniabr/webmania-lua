"""Coherent small fixtures and exact-size PDF streams for local parser controls."""
from pathlib import Path

FIXTURES=Path(__file__).resolve().parent/'fixtures'
PDF=(FIXTURES/'canonical_plain.pdf').read_bytes()
PROTECTED_PDF=(FIXTURES/'canonical_protected.pdf').read_bytes()
XLSX=(FIXTURES/'canonical_xlsx.xlsx').read_bytes()

def pdf_with_stream(total_bytes, markers=()):
    """Keep requested absolute byte markers inside an uninterpreted PDF stream."""
    payload_size=total_bytes
    for _ in range(8):
        prefix=b'%PDF-1.4\n'
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Resources << >> /Contents 4 0 R >>']
        offsets=[0]
        for number,body in enumerate(objects,1):
            offsets.append(len(prefix));prefix+=str(number).encode()+b' 0 obj\n'+body+b'\nendobj\n'
        offsets.append(len(prefix));prefix+=b'4 0 obj\n<< /Length '+str(payload_size).encode()+b' >>\nstream\n'
        payload=bytearray(b'a'*payload_size)
        for absolute,value in markers:
            relative=absolute-len(prefix)
            if not 0<=relative<payload_size:raise ValueError('Marker is outside stream')
            payload[relative]=value
        suffix=b'\nendstream\nendobj\n'
        xref=len(prefix)+payload_size+len(suffix)
        suffix+=b'xref\n0 5\n0000000000 65535 f \n'
        for offset in offsets[1:]:suffix+=f'{offset:010d} 00000 n \n'.encode()
        suffix+=b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
        actual=len(prefix)+payload_size+len(suffix)
        if actual==total_bytes:return prefix+payload+suffix
        payload_size-=actual-total_bytes
        if payload_size<0:raise ValueError('PDF target is too small')
    raise ValueError('PDF target did not converge')
