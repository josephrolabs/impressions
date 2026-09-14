def solve(lines):
    result=[]
    for line in lines:
        line=line.strip()
        if not line: continue
        if "<" not in line or not line.endswith("> ".strip()): raise ValueError("malformed")
        name,email=line.rsplit("<",1); email=email[:-1]
        if not name.strip() or "@" not in email: raise ValueError("malformed")
        result.append({"name":name.strip(),"email":email})
    return result
