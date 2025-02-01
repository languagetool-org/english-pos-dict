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



# added.txt
echo "# A part-of-speech dictionary that's used additionally to the binary dictionary (*.dict).
# This does not add words to the spell checker, see hunspell/spelling.txt for that.
# File Encoding: UTF-8
# Format: three tab-separated fields: fullform baseform postags" > added.txt
grep -E "^< " tagger-dictionary.diff >> added.txt
sed -i 's/^< //g' added.txt

# removed.txt
echo "# The opposite of added.txt: these readings will be removed.
# Useful to remove incorrect readings from the binary dictionary without rebuilding it.
# File Encoding: UTF-8
# Format: fullform baseform postags (tab separated)" > removed.txt
grep -E "^> " tagger-dictionary.diff >> removed.txt
sed -i 's/^> //g' removed.txt

# spelling.txt
echo "# Words that extend the spell checker. See ignore.txt for words that should be
# completely ignored (i.e. not used to create suggestions).
# You can use space-separated tokens here, but for phrases like 'DD/MM/YYYY' that get
# split into several tokens, use multiwords.txt or disambiguation.xml." > spelling.txt
grep -E "^< " en_ALL.diff >> spelling.txt
sed -i 's/^< //g' spelling.txt

path="../../languagetool/languagetool-language-modules/en/src/main/resources/org/languagetool/resource/en/"

for country in AU CA GB NZ US ZA; do
  echo "# Words that extend the en-${country} spell checker.
# To add a word to all variants (en-US, en-GB,...) use spelling.txt
# For multi-word terms, refer to https://github.com/languagetool-org/languagetool/issues/700" > spelling_en-${country}.txt
  grep -E "^< " en_${country}.diff >> spelling_en-${country}.txt
  sed -i 's/^< //g' spelling_en-${country}.txt
  cp spelling_en-${country}.txt "${path}hunspell/"
done



cp added.txt "$path"
cp removed.txt "$path"
cp spelling.txt "${path}hunspell/"