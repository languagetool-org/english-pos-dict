#!/bin/bash

lt_version=6.4-SNAPSHOT
lt_tools=../languagetool/languagetool-standalone/target/LanguageTool-${lt_version}/LanguageTool-${lt_version}/languagetool.jar

#to be updated
#src_dict=./original-files-december-2023
src_dict=..//languagetool/languagetool-language-modules/en/src/main/resources/org/languagetool/resource/en

rm -rf tagger-dict
mkdir tagger-dict

# dump the tagger dictionary
java -cp $lt_tools org.languagetool.tools.DictionaryExporter -i $src_dict/english.dict -o ./tagger-dict/english-tagger-original.txt -info $src_dict/english.info

cp $src_dict/added.txt tagger-dict
cp $src_dict/removed.txt tagger-dict

cd tagger-dict
sed -i 's/#.*$//' added.txt
sed -i '/^$/d' added.txt
sed -i -e '$a\' added.txt
sed -i 's/#.*$//' removed.txt
sed -i '/^$/d' removed.txt
sed -i -e '$a\' removed.txt
iconv -f ISO-8859-1 -t UTF-8 english-tagger-original.txt > english-tagger-original-utf8.txt
cat added.txt english-tagger-original-utf8.txt > english-tagger-added.txt
export LC_ALL=C && sort -u -o removed.txt removed.txt
export LC_ALL=C && sort -u -o english-tagger-added.txt english-tagger-added.txt
comm -23 english-tagger-added.txt removed.txt > english-tagger.txt
export LC_ALL=C && sort -u -o english-tagger-original-utf8.txt english-tagger-original-utf8.txt
export LC_ALL=C && sort -u -o english-tagger.txt english-tagger.txt
diff english-tagger-original-utf8.txt english-tagger.txt >> english-tagger.diff
cd -

target_dir=src/main/resources/org/languagetool/resource/en

#create tagger binary
java -cp $lt_tools org.languagetool.tools.POSDictionaryBuilder -i ./tagger-dict/english-tagger.txt -info ${target_dir}/english.info -o ${target_dir}/english.dict

#create synth binary
cp $src_dict/filter-archaic.txt tagger-dict
cp $src_dict/do-not-synthesize.txt tagger-dict
cd tagger-dict
sed -i 's/#.*$//' do-not-synthesize.txt
sed -i '/^$/d' do-not-synthesize.txt
# filter-archaic.txt has to be in the folder of english_synth.info
cat do-not-synthesize.txt >> filter-archaic.txt
cp ../${target_dir}/english_synth.info .
java -cp ../$lt_tools org.languagetool.tools.SynthDictionaryBuilder -i english-tagger.txt -info english_synth.info -o ../${target_dir}/english_synth.dict
cd -
mv ${target_dir}/english_synth.dict_tags.txt ${target_dir}/english_tags.txt

diff $src_dict/english_tags.txt ${target_dir}/english_tags.txt > tagger-dict/english_tags.diff

#dump synth dict
java -cp $lt_tools org.languagetool.tools.DictionaryExporter -i ${target_dir}/english_synth.dict -o ./tagger-dict/english_synth_lt.txt -info ${target_dir}/english_synth.info