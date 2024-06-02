import re

def clean_line(s):
  return s.split('#')[0].strip()

def getLemmaAndExtra(lemma):
  pattern = r"^(.+?) \[(.+?)\]$"
  match = re.search(pattern, lemma)
  extra = ""
  if match:
    lemma = match.group(1)
    extra = match.group(2)
  return lemma, extra

def getDuplicateConsonant(extra):
  results = []
  patternDuplicateConsonant1 = r"^\-(([^aeiouywh])\2)-$"
  match = re.search(patternDuplicateConsonant1,extra)
  if match:
    results.append(match.group(1))
  #patternDuplicateConsonant2 = r"^\-(([^aeiouywh])\2)-,-(\2)-$"
  #match = re.search(patternDuplicateConsonant2,extra)
  #if match:
  #  results.append(match.group(1))
  #  results.append(match.group(2))
  return results


def getInflectedFormsAndTags(lemma, pos, extra=''):
  forms = ""
  patternCVC = r"^[^aeiou]+[aeiou][^aeiou]$"
  patternDuplicateConsonant = r"^\-([^aeiouywh])\1\-$"
  vowels = "aeiou";
  # inflection of regular verbs
  if pos=="verb":
    duplicate_consonant_list = getDuplicateConsonant(extra)
    if len(duplicate_consonant_list) == 1:
      duplicate_consonant = extra[1]
      forms = "-/VB,-$ed/VBD,-$ing/VBG,-$ed/VBN,-/VBP,-s/VBZ".replace("-", lemma).replace("$", duplicate_consonant)
    #elif len(duplicate_consonant_list) == 2:
    #  duplicate_consonant = extra[1]
    #  forms = "-/VB,-ed/VBD,-$ed/VBD,-ing/VBG,-$ing/VBG,-ed/VBN,-$ed/VBN,-/VBP,-s/VBZ".replace("-", lemma).replace("$", duplicate_consonant)
    elif lemma.endswith("e"):
      root = lemma[:-1]
      forms = "-e/VB,-ed/VBD,-ing/VBG,-ed/VBN,-e/VBP,-es/VBZ".replace("-", root)
    elif len(lemma)>2 and lemma[-1]==("y") and lemma[-2] not in vowels:
      root = lemma[:-1]
      forms = "-y/VB,-ied/VBD,-ying/VBG,-ied/VBN,-y/VBP,-ies/VBZ".replace("-", root)
    elif len(lemma)>2 and (lemma.endswith("x") or lemma.endswith("sh") or lemma.endswith("ss") or lemma.endswith("ch") or (lemma.endswith("s") and lemma[-2] in vowels)):
      forms = "-/VB,-ed/VBD,-ing/VBG,-ed/VBN,-/VBP,-es/VBZ".replace("-", lemma)
    elif re.search(patternCVC,lemma): 
      # duplicate the last consonant: hug -> hugged
      forms = "-/VB,-$ed/VBD,-$ing/VBG,-$ed/VBN,-/VBP,-s/VBZ".replace("-", lemma).replace("$", lemma[-1])
      # for verbs with more than one syllable, it cannot be done because 
      # we don't know which syllable is stressed (prefer/preferred, visit/visited, admit/admitted)
    else:
      forms = "-/VB,-ed/VBD,-ing/VBG,-ed/VBN,-/VBP,-s/VBZ".replace("-", lemma)

  #inflection of regular nouns
  if pos.startswith("noun"):
    add_string = ""
    parts = pos.split("_")
    if len(parts) == 2:
      if parts[1] == "UN":
        add_string = ":UN"
      if parts[1] == "U":
        add_string = ":U"
    if len(extra)>0:
      forms = lemma+"/NN"+add_string
      plurals = extra.replace("pl.","").strip()
      for plural in plurals.split(","):
        plural = plural.strip()
        forms = forms+","+plural+"/NNS"
    elif len(lemma)>1 and (lemma[-2:] in ["ch","sh"] or lemma[-1] in "sxz"):
      forms = "-/NN,-es/NNS".replace("-", lemma)
    #potato/potatoes  
    #elif lemma[-2] not in vowels and lemma[-1]=="o":
    #  forms = "-/NN,-es/NNS".replace("-", lemma)
    elif len(lemma)>1 and lemma[-1]==("y") and lemma[-2] not in vowels:
      forms = lemma + "/NN,"+lemma[:-1]+"ies/NNS"
    else:
      forms = lemma + "/NN,"+lemma+"s/NNS"
    if add_string != "":
      forms = forms.replace("NN,", "NN"+add_string+",")
  if forms=="":
    if extra != "":
      print("ERROR: cannot generate forms with lemma and pos: " + lemma + " ["+extra+"]=" + pos)
    else:
      #print("ERROR: cannot generate forms with lemma and pos: " + lemma + "=" + pos)
      forms = lemma+"/"+pos
  return forms

def getFormTagLemma(forms_tags, lemma, variants):
  inflected_forms = []
  if "/" in forms_tags:
    for form_tag in forms_tags.split(","):
       form, tag = tuple(form_tag.split("/"))
       inflected_forms.append(form+" "+lemma+" "+tag+" "+variants)
    return inflected_forms

def getFormsFromLine(line):
  #print(line)
  line = clean_line(line)
  inflected_forms = []
  if line == "":
    return inflected_forms
  parts = line.split("=")
  lemmas = parts[0]
  forms_tags = parts[1]
  variants = parts[2]
  if "," in forms_tags:
    return getFormTagLemma(forms_tags, lemmas, variants)
  variants_groups = variants.split("|") 
  for i,lemma in enumerate(lemmas.split("|")):
    lemma, extra = getLemmaAndExtra(lemma)
    inflected_forms_tags = getInflectedFormsAndTags(lemma, forms_tags, extra)
    inflected_forms.extend(getFormTagLemma(inflected_forms_tags, lemma, variants_groups[i])) 
  return inflected_forms

#behold/VB,beheld/VBD,beholding/VBG,beheld/VBN,behold/VBP,beholds/VBZ
def isErrorInVerbalForms(tag_forms_dict, lemma):
  verb_tags = ["VB", "VBP", "VBZ", "VBD", "VBN", "VBG"]
  is_error = False
  if lemma in ["do", "have", "methinks", "be"]:
    return is_error
  if set(tag_forms_dict.keys()) != set(verb_tags):
    print ("ERROR: incomplete set of tags: " + str(tag_forms_dict))
    is_error = True
  if any(not s.endswith("s") for s in tag_forms_dict["VBZ"]):
    print ("ERROR: VBZ form must end with -s: " + str(tag_forms_dict))
    is_error = True
  if any(not s.endswith("ing") for s in tag_forms_dict["VBG"]):
    print ("ERROR: VBG form must end with -ing: " + str(tag_forms_dict))
    is_error = True
  if len(tag_forms_dict["VB"])>1:
    print ("ERROR: only one base form is expected: " + str(tag_forms_dict))
    is_error = True
  if lemma == "be":
    return is_error
  if len(tag_forms_dict["VBP"])>1:
    print ("ERROR: only one VBP is expected: " + str(tag_forms_dict))
    is_error = True
  if len(tag_forms_dict["VB"])==1 and len(tag_forms_dict["VBP"])==1 and tag_forms_dict["VB"][0]!=tag_forms_dict["VBP"][0]:
    print ("ERROR: VB and VBP forms are expected to be equal: " + str(tag_forms_dict))
    is_error = True
  if len(tag_forms_dict["VB"])==1 and tag_forms_dict["VB"][0]!=lemma:
    print ("ERROR: lemma is expected to be equal to VB form: " + str(tag_forms_dict))
    is_error = True
  return is_error


def parseVerbalForms(line):
  line = clean_line(line)
  parts = line.split("=")
  if len(parts)!=3:
    return
  lemmas = parts[0]
  forms_tags = parts[1]
  variants = parts[2]
  tag_forms_dict = {}
  if lemmas in ["do", "have", "methinks", "be"]:
    return line
  for form_tag in forms_tags.split(","):
    form, tag = tuple(form_tag.split("/"))
    if tag in tag_forms_dict:
      tag_forms_dict[tag].append(form)
    else:
      tag_forms_dict[tag] = [form]
  if not isErrorInVerbalForms(tag_forms_dict, lemmas):
    # "VBZ", "VBD", "VBN", "VBG"
    new_line = lemmas+" ["+",".join(tag_forms_dict["VBZ"])+";"+",".join(tag_forms_dict["VBD"])+";" + ",".join(tag_forms_dict["VBN"])+";" + ",".join(tag_forms_dict["VBG"])+"]=verb="+variants
    return new_line
  return "ERROR: "+line

  

  
  




#examples
assert getInflectedFormsAndTags("add", "verb") == "add/VB,added/VBD,adding/VBG,added/VBN,add/VBP,adds/VBZ"
assert getInflectedFormsAndTags("wish", "verb") == "wish/VB,wished/VBD,wishing/VBG,wished/VBN,wish/VBP,wishes/VBZ"
assert getInflectedFormsAndTags("portray", "verb") == "portray/VB,portrayed/VBD,portraying/VBG,portrayed/VBN,portray/VBP,portrays/VBZ"
assert getInflectedFormsAndTags("specify", "verb") == "specify/VB,specified/VBD,specifying/VBG,specified/VBN,specify/VBP,specifies/VBZ"
assert getInflectedFormsAndTags("hug", "verb") == "hug/VB,hugged/VBD,hugging/VBG,hugged/VBN,hug/VBP,hugs/VBZ"
# doesn't work for irregular verbs
assert getInflectedFormsAndTags("run", "verb") != "run/VB,ran/VBD,running/VBG,run/VBN,run/VBP,runs/VBZ"

assert getInflectedFormsAndTags("baby", "noun") == "baby/NN,babies/NNS"
assert getInflectedFormsAndTags("army", "noun") == "army/NN,armies/NNS"
assert getInflectedFormsAndTags("cat", "noun") == "cat/NN,cats/NNS"
assert getInflectedFormsAndTags("student", "noun") == "student/NN,students/NNS"
assert getInflectedFormsAndTags("video", "noun") == "video/NN,videos/NNS"
assert getInflectedFormsAndTags("radio", "noun") == "radio/NN,radios/NNS"
assert getInflectedFormsAndTags("toy", "noun") == "toy/NN,toys/NNS"
assert getInflectedFormsAndTags("day", "noun") == "day/NN,days/NNS"
assert getInflectedFormsAndTags("church", "noun") == "church/NN,churches/NNS"
assert getInflectedFormsAndTags("bench", "noun") == "bench/NN,benches/NNS"
assert getInflectedFormsAndTags("brush", "noun") == "brush/NN,brushes/NNS"
assert getInflectedFormsAndTags("dish", "noun") == "dish/NN,dishes/NNS"
assert getInflectedFormsAndTags("class", "noun") == "class/NN,classes/NNS"
assert getInflectedFormsAndTags("kiss", "noun") == "kiss/NN,kisses/NNS"
assert getInflectedFormsAndTags("fox", "noun") == "fox/NN,foxes/NNS"
assert getInflectedFormsAndTags("topaz", "noun") == "topaz/NN,topazes/NNS"
assert getInflectedFormsAndTags("buzz", "noun") == "buzz/NN,buzzes/NNS"

# doesn't work for irregular nouns
assert getInflectedFormsAndTags("man", "noun") != "man/NN,men/NNS"

# not implemented, but could be
assert getInflectedFormsAndTags("thief", "noun") != "thief/NN,thieves/NNS"
assert getInflectedFormsAndTags("life", "noun") != "life/NN,lives/NNS"
assert getInflectedFormsAndTags("potato", "noun") != "potato/NN,potatoes/NNS"
assert getInflectedFormsAndTags("echo", "noun") != "echo/NN,echoes/NNS"


#print (getInflectedFormsAndTags("shilly-shally", "verb"))
#print (getInflectedFormsAndTags("program", "verb", "-mm-"))
#print (getInflectedFormsAndTags("co-star", "verb", "-rr-"))

#getFormsFromLine("j [pl. js,j's]=noun=all")
#print (getFormsFromLine("pommel=pommel/VB,pommeled/VBD,pommelled/VBD,pommeling/VBG,pommelling/VBG,pommeled/VBN,pommelled/VBN,pommel/VBP,pommels/VBZ=all"))
#print (getFormsFromLine("pomelo=noun=all"))
#print (getFormsFromLine("honor|honour=noun_UN=us|gb,ca,au,nz,za"))
#print (getFormsFromLine("honor|honour=verb=us|gb,ca,au,nz,za"))


