#!/bin/bash

lt_version=6.6-SNAPSHOT
lt_tools=../../languagetool/languagetool-standalone/target/LanguageTool-${lt_version}/LanguageTool-${lt_version}/languagetool.jar


# Get old binaries
old_dicts_path=~/.m2/repository/org/languagetool/english-pos-dict/0.5/english-pos-dict-0.5.jar
jar xf $old_dicts_path

# Dump the tagger dictionary
path="./org/languagetool/resource/en/"
java -cp $lt_tools org.languagetool.tools.DictionaryExporter -i "${path}english.dict" -o tagger-dictionary.txt -info "${path}english.info"

# Dump the speller dictionaries
for country in AU CA GB NZ US ZA; do
  java -cp $lt_tools org.languagetool.tools.DictionaryExporter -i "${path}hunspell/en_${country}.dict" -o en_${country}.txt -info "${path}hunspell/en_${country}.info"
done

# Compare tagger
diff <(export LC_ALL=C && sort -u ../src-dict/output/tagger-dictionary.txt) <(export LC_ALL=C && sort -u tagger-dictionary.txt) > tagger-dictionary.diff

python3 prepare-spelling-dicts-for-comparison.py

# Compare spellers
for country in AU CA GB NZ US ZA; do
diff <(export LC_ALL=C &&  sort -u ../src-dict/output/en_${country}.txt) <(export LC_ALL=C && sort -u en_${country}.txt) > en_${country}.diff
done

diff <(export LC_ALL=C &&  sort -u ../src-dict/output/en_ALL.txt) <(export LC_ALL=C && sort -u en_ALL.txt) > en_ALL.diff

#TODO: create files added.txt, removed.txt. spelling.txt (for variants)