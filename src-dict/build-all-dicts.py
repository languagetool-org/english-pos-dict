import inflection

tagger_file = open("./src-dict/output/tagger-dictionary.txt", "w")

all_variants = ["us", "gb", "ca", "nz", "au", "za"]
spelling_dicts = {}
for myvariant in all_variants:
  spelling_dicts[myvariant] = {}

for file_path in ["./src-dict/src-clean.txt"]: #,"./src-dict/src-pending.txt"
  with open(file_path, "r") as file:
    for line in file.readlines():
      form_lines = inflection.getFormsFromLine(line)
      if len(form_lines)>0:
        for form_line in form_lines:
          if form_line:
            parts = form_line.split("\t")
            form = parts[0]
            variants = parts[3]
            tagger_file.write(form+"\t"+parts[1]+"\t"+parts[2]+"\n")
            for variant in variants.split(","):
              if variant == "all":
                for myvariant in all_variants:
                  spelling_dicts[myvariant][form] = ""
              if variant in all_variants:
                spelling_dicts[variant][form] = ""
      #else:
        #print ("Cannot build from line:" + line)      

for myvariant in all_variants:
  spell_dict = dict(sorted(spelling_dicts[myvariant].items()))

  output_file = open("./src-dict/output/en_"+myvariant.upper()+".txt", "w")
  for key in spell_dict.keys():
    output_file.write(key+"\n")
  output_file.close()