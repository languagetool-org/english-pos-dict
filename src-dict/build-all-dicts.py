"""Builds English dictionaries for multiple regional variants and part-of-speech tagging.

This module processes source dictionary files to generate:
1. A part-of-speech tagger dictionary with word forms, lemmas and tags
2. Separate spelling dictionaries for different English variants (US, GB, CA, NZ, AU, ZA)

Input:
    ./src-dict/src-clean.txt: Source dictionary file with word entries

Output:
    ./src-dict/output/tagger-dictionary.txt: Tagged dictionary for POS tagging
    ./src-dict/output/en_XX.txt: Spelling dictionaries (XX = US/GB/CA/NZ/AU/ZA/ALL)

The module skips certain tags like 'untagged', 'punctuation', 'abbreviation',
'symbol' and 'contraction' when building the tagger dictionary.
"""

import inflection

tagger_file = open("./src-dict/output/tagger-dictionary.txt", "w", encoding="utf-8")

all_variants = ["us", "gb", "ca", "nz", "au", "za", "all"]
tags_to_avoid = ["untagged", "punctuation", "abbreviation", "symbol", "contraction"]
spelling_dicts = {}
for myvariant in all_variants:
    spelling_dicts[myvariant] = {}

for file_path in ["./src-dict/src-clean.txt"]:  # ,"./src-dict/src-pending.txt"
    with open(file_path, "r", encoding='utf-8') as file:
        tagger_file.write("#\t#\t#\n")
        tagger_file.write(",\t,\t,\n")
        tagger_file.write(".\t.\t.\n")
        for line in file.readlines():
            form_lines = inflection.getFormsFromLine(line)
            if len(form_lines) > 0:
                for form_line in form_lines:
                    if form_line:
                        parts = form_line.split("\t")
                        form = parts[0]
                        lemma = parts[1]
                        tag = parts[2]
                        variants = parts[3]
                        if tag not in tags_to_avoid:
                            tagger_file.write(form + "\t" + lemma + "\t" + tag + "\n")
                        for variant in variants.split(","):
                            # if variant == "all":
                            #  for myvariant in all_variants:
                            #    spelling_dicts[myvariant][form] = ""
                            if variant in all_variants:
                                spelling_dicts[variant][form] = ""
            # else:
            # print ("Cannot build from line:" + line)

for myvariant in all_variants:
    spell_dict = dict(sorted(spelling_dicts[myvariant].items()))

    output_file = open("./src-dict/output/en_" + myvariant.upper() + ".txt", "w", encoding="utf-8")
    for key in spell_dict.keys():
        output_file.write(key + "\n")
    output_file.close()
