
import json
d = {"nodes":[],"edges":[],"hyperedges":[],"input_tokens":0,"output_tokens":0}
N,E,H = d["nodes"],d["edges"],d["hyperedges"]
def n(i,l,t,s,a=None): N.append({"id":i,"label":l,"file_type":t,"source_file":s,"source_location":None,"source_url":None,"captured_at":None,"author":a,"contributor":None})
def e(s,t,r,c,cs,f,w=1.0): E.append({"source":s,"target":t,"relation":r,"confidence":c,"confidence_score":cs,"source_file":f,"source_location":None,"weight":w})
print("script loaded")
