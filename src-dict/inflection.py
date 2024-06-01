import re

def getInflectedForms(lemma, pos, extra=''):
  forms = ""
  patternCVC = r"^[^aeiou]+[aeiou][^aeiou]$"
  patternDuplicateConsonant = r"^\-([^aeiouywh])\1\-$"
  vowels = "aeiou";
  # inflection of regular verbs
  if pos=="verb":
    if lemma.endswith("e"):
      root = lemma[:-1]
      forms = "-e/VB,-ed/VBD,-ing/VBG,-ed/VBN,-e/VBP,-es/VBZ".replace("-", root)
    elif len(lemma)>2 and lemma[-1]==("y") and lemma[-2] not in vowels:
      root = lemma[:-1]
      forms = "-y/VB,-ied/VBD,-ying/VBG,-ied/VBN,-y/VBP,-ies/VBZ".replace("-", root)
    elif lemma.endswith("sh") or lemma.endswith("ss") or lemma.endswith("ch"):
      forms = "-/VB,-ed/VBD,-ing/VBG,-ed/VBN,-/VBP,-es/VBZ".replace("-", lemma)
    elif re.search(patternCVC,lemma): 
      # duplicate the last consonant: hug -> hugged
      forms = "-/VB,-$ed/VBD,-$ing/VBG,-$ed/VBN,-/VBP,-s/VBZ".replace("-", lemma).replace("$", lemma[-1])
      # for verbs with more than one syllable, it cannot be done because 
      # we don't know which syllable is stressed (prefer/preferred, visit/visited, admit/admitted)
    elif extra!="" and re.search(patternDuplicateConsonant,extra):
      duplicateConsonant = extra[1]
      forms = "-/VB,-$ed/VBD,-$ing/VBG,-$ed/VBN,-/VBP,-s/VBZ".replace("-", lemma).replace("$", duplicateConsonant)
    else:
      forms = "-/VB,-ed/VBD,-ing/VBG,-ed/VBN,-/VBP,-s/VBZ".replace("-", lemma)

  #inflection of regular nouns
  if pos.startswith("noun") and len(lemma)>1:
    add_string = ""
    parts = pos.split("_")
    if len(parts) == 2:
      if parts[1] == "UN":
        add_string = ":UN"
      if parts[1] == "U":
        add_string = ":U"
    if lemma[-2:] in ["ch","sh"] or lemma[-1] in "sxz":
      forms = "-/NN,-es/NNS".replace("-", lemma)
    #potato/potatoes  
    #elif lemma[-2] not in vowels and lemma[-1]=="o":
    #  forms = "-/NN,-es/NNS".replace("-", lemma)
    elif lemma[-1]==("y") and lemma[-2] not in vowels:
      forms = lemma + "/NN,"+lemma[:-1]+"ies/NNS"
    else:
      forms = lemma + "/NN,"+lemma+"s/NNS"
    if add_string != "":
      forms = forms.replace("NN,", "NN"+add_string+",")
  return forms


#examples
assert getInflectedForms("add", "verb") == "add/VB,added/VBD,adding/VBG,added/VBN,add/VBP,adds/VBZ"
assert getInflectedForms("wish", "verb") == "wish/VB,wished/VBD,wishing/VBG,wished/VBN,wish/VBP,wishes/VBZ"
assert getInflectedForms("portray", "verb") == "portray/VB,portrayed/VBD,portraying/VBG,portrayed/VBN,portray/VBP,portrays/VBZ"
assert getInflectedForms("specify", "verb") == "specify/VB,specified/VBD,specifying/VBG,specified/VBN,specify/VBP,specifies/VBZ"
assert getInflectedForms("hug", "verb") == "hug/VB,hugged/VBD,hugging/VBG,hugged/VBN,hug/VBP,hugs/VBZ"
# doesn't work for irregular verbs
assert getInflectedForms("run", "verb") != "run/VB,ran/VBD,running/VBG,run/VBN,run/VBP,runs/VBZ"

assert getInflectedForms("baby", "noun") == "baby/NN,babies/NNS"
assert getInflectedForms("army", "noun") == "army/NN,armies/NNS"
assert getInflectedForms("cat", "noun") == "cat/NN,cats/NNS"
assert getInflectedForms("student", "noun") == "student/NN,students/NNS"
assert getInflectedForms("video", "noun") == "video/NN,videos/NNS"
assert getInflectedForms("radio", "noun") == "radio/NN,radios/NNS"
assert getInflectedForms("toy", "noun") == "toy/NN,toys/NNS"
assert getInflectedForms("day", "noun") == "day/NN,days/NNS"
assert getInflectedForms("church", "noun") == "church/NN,churches/NNS"
assert getInflectedForms("bench", "noun") == "bench/NN,benches/NNS"
assert getInflectedForms("brush", "noun") == "brush/NN,brushes/NNS"
assert getInflectedForms("dish", "noun") == "dish/NN,dishes/NNS"
assert getInflectedForms("class", "noun") == "class/NN,classes/NNS"
assert getInflectedForms("kiss", "noun") == "kiss/NN,kisses/NNS"
assert getInflectedForms("fox", "noun") == "fox/NN,foxes/NNS"
assert getInflectedForms("topaz", "noun") == "topaz/NN,topazes/NNS"
assert getInflectedForms("buzz", "noun") == "buzz/NN,buzzes/NNS"

# doesn't work for irregular nouns
assert getInflectedForms("man", "noun") != "man/NN,men/NNS"

# not implemented, but could be
assert getInflectedForms("thief", "noun") != "thief/NN,thieves/NNS"
assert getInflectedForms("life", "noun") != "life/NN,lives/NNS"
assert getInflectedForms("potato", "noun") != "potato/NN,potatoes/NNS"
assert getInflectedForms("echo", "noun") != "echo/NN,echoes/NNS"

print ( getInflectedForms("lustre", "verb"))
print ( getInflectedForms("cosy", "verb"))
print (getInflectedForms("program", "verb", "-mm-"))
print (getInflectedForms("co-star", "verb", "-rr-"))