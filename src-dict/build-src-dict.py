from collections import defaultdict

dict_by_lemma = {}

def getRegular(s):
  parts = s.split("=")
  lemma = parts[0].strip()
  formstags = parts[1]
  if lemma.endswith("e"):
    formstags = formstags.replace(lemma[:-1],"")
    if formstags == "e/VB,ed/VBD,ing/VBG,ed/VBN,e/VBP,es/VBZ":
      return "\n" + lemma + "=verb="
  formstags = parts[1]
  if lemma.endswith("y"):
    formstags = formstags.replace(lemma[:-1],"")
    if formstags == "y/VB,ied/VBD,ying/VBG,ied/VBN,y/VBP,ies/VBZ":
      return "\n" + lemma + "=verb="
  formstags = parts[1]
  if lemma.endswith("sh") or lemma.endswith("ss") or lemma.endswith("ch"):
    formstags = formstags.replace(lemma,"")
    if formstags == "/VB,ed/VBD,ing/VBG,ed/VBN,/VBP,es/VBZ":
      return "\n" + lemma + "=verb="
  formstags = parts[1]
  formstags = formstags.replace(lemma, "")
  if formstags == "/VB,ed/VBD,ing/VBG,ed/VBN,/VBP,s/VBZ":
    return "\n" + lemma + "=verb="
  
  return s
      
# read spelling dicts
variants = ["au", "ca", "gb", "nz", "us", "za"]
spell_dict = {
  'au': {}, 'ca': {}, 'gb': {}, 'nz': {}, 'us': {}, 'za': {}
}
for variant in variants:
  file_path = '../spell-dicts/en_'+variant.upper()+'.txt'
  with open(file_path, 'r') as file:
    for line in file.readlines():
      line = line.strip()
      spell_dict[variant][line] = 0
#TODO: add large US spelling dict

file_path = '../tagger-dict/english-tagger.txt'
with open(file_path, 'r') as file:
  for line in file:
    parts = line.strip().split("\t")
    form = parts[0]
    lemma = parts[1]
    postag = parts[2]
    if lemma in dict_by_lemma:
      dict_by_lemma[lemma] = dict_by_lemma[lemma] + ", "+form+"/"+postag
    else:
      dict_by_lemma[lemma] = form+"/"+postag

outputfile = open("english-src-dict.txt", 'w')
#sorted_dict = dict(sorted(dict_by_lemma.items()))


for lemma,forms_tags_str in sorted(dict_by_lemma.items()):
  #outputfile.write("\n>>"+lemma+"="+forms_tags_str+"\n")
  found_in_variants = ""
  # get variants where lemma exists
  for variant in variants:
    if lemma in spell_dict[variant]:
      found_in_variants=found_in_variants+","+variant
  found_in_variants=found_in_variants[1:]
  if found_in_variants=="au,ca,gb,nz,us,za":
    found_in_variants="all"
  if found_in_variants=="":
    found_in_variants="none"
  forms_tags = forms_tags_str.split(",")
  tags_forms_dict = defaultdict(list)
  for form_tag in forms_tags:
    (form, tag) = form_tag.strip().split("/")
    form = form.strip()
    tag = tag.strip()
    tags_forms_dict[tag].append(form)
  tags_forms_dict = dict(sorted(tags_forms_dict.items()))
  # mark forms as "used" in the spelling dicts
  for forms_list in tags_forms_dict.values():
    for form in forms_list:
      for variant in variants:
        if form in spell_dict[variant]:
          spell_dict[variant][form] = 1
  if len(tags_forms_dict)==1:
    tag, forms = tags_forms_dict.popitem()
    outputfile.write("\n"+lemma+"=")
    if len(forms)==1:
      outputfile.write(tag)
      if form!=lemma:
        print ("WARNING form!=lemma: "+lemma+" "+forms_tags_str)
    else:
      first = True
      for form in forms:
        if first:
          first = False
        else:
          outputfile.write(",")  
        outputfile.write(form+"/"+tag)
    outputfile.write("="+found_in_variants)
  else:
    prev_first_char = ""
    outputline = ""
    for tag,forms in tags_forms_dict.items():
      first_char = tag[0]
      if first_char != prev_first_char:
        if prev_first_char != "":
          outputline = outputline + "="
          outputfile.write(getRegular(outputline))
          outputfile.write(found_in_variants)
          outputline = ""
        outputline = outputline +"\n"+lemma+"="
      else:
        outputline = outputline + ","
      for form in forms:
        if not outputline.endswith(",") and not outputline.endswith("="):
          outputline = outputline + ","  
        outputline = outputline + form+"/"+tag
      prev_first_char = first_char
    outputline = outputline + "="
    outputfile.write(getRegular(outputline)) 
    outputfile.write(found_in_variants)



for variant in variants:
  for word in spell_dict[variant]:
    #print(variant, word, spell_dict[variant][word])
    if spell_dict[variant][word] == 0:
      found_in_variants=""
      for variant2 in variants:
        if word in spell_dict[variant2]:
          found_in_variants=found_in_variants+","+variant2
          spell_dict[variant2][word] = 1
      found_in_variants=found_in_variants[1:]
      if found_in_variants=="au,ca,gb,nz,us,za":
        found_in_variants="all"
      if found_in_variants=="":
        found_in_variants="none"
      outputfile.write("\n"+word+"=UNTAGGED="+found_in_variants)

    