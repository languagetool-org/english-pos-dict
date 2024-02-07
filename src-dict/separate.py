file_path = 'english-src-dict.txt'

discarded_output = open("src-discarded.txt", "w")
clean_output = open("src-clean.txt", "w")
pending_output = open("src-pending.txt", "w")

def starts_with_prefix(string):
    prefixes_gb = ["mis", "out", "over", "re", "under"]
    for prefix in prefixes_gb:
        if string.startswith(prefix):
            return True
    if string.startswith("in") and string[2].isupper():
       return True
    return False

with open(file_path, 'r') as file:
  for line in file:
    line = line.strip()
    parts = line.split("=")
    if len(parts)<3:
       continue
    lemma = parts[0]
    tag = parts[1]
    variants = parts[2]
    if tag != "UNTAGGED" and variants=="all":
      clean_output.write(line + "\n")
    elif tag != "UNTAGGED" and "gb" in variants and "us" in variants:
      clean_output.write(lemma + "=" + tag + "=all\n")
    elif tag == "UNTAGGED" and variants == "gb" and starts_with_prefix(lemma):
       discarded_output.write(line + "\n")
    else:
      pending_output.write(line + "\n")
    
      
