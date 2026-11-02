import hashlib,os,sys
if os.geteuid()==0: raise SystemExit("Payload reader must remain unprivileged")
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,"rb") as stream: data=stream.read()
if hashlib.sha256(data).hexdigest()!=sys.argv[2]: raise SystemExit("Source hash mismatch; no bytes emitted")
sys.stdout.buffer.write(data)
