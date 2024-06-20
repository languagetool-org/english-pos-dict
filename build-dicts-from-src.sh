#!/bin/bash

for file in ./src-dict/src-pending.txt ./src-dict/src-clean.txt
do
	export LC_ALL=C && sort -u $file -o $file
done

python3 src-dict/check-syntax.py 
python3 src-dict/build-all-dicts.py

export LC_ALL=C && sort -u -o ./src-dict/output/tagger-dictionary.txt ./src-dict/output/tagger-dictionary.txt
for variant in AU CA GB NZ US ZA
do
	export LC_ALL=C && sort -u -o ./src-dict/output/en_${variant}.txt ./src-dict/output/en_${variant}.txt
done


lt_version=6.5-SNAPSHOT
lt_tools=../languagetool/languagetool-standalone/target/LanguageTool-${lt_version}/LanguageTool-${lt_version}/languagetool.jar

#to be updated
#src_dict=./original-files-december-2023
src_dict=../languagetool/languagetool-language-modules/en/src/main/resources/org/languagetool/resource/en

target_dir=src/main/resources/org/languagetool/resource/en

rm -rf tmp
mkdir tmp

cp ./src-dict/output/tagger-dictionary.txt ./tmp/
cp ./info-files/english.info ${target_dir}/english.info

#create tagger binary
java -cp $lt_tools org.languagetool.tools.POSDictionaryBuilder -i ./tmp/tagger-dictionary.txt -info ./info-files/english.info -o ${target_dir}/english.dict


#create synth binary
cp $src_dict/filter-archaic.txt ./tmp/
cp $src_dict/do-not-synthesize.txt ./tmp/
cp ./info-files/english_synth.info ./tmp/
cp ./info-files/english_synth.info ./${target_dir}/english_synth.info
cd ./tmp
sed -i 's/#.*$//' do-not-synthesize.txt
sed -i '/^$/d' do-not-synthesize.txt
# filter-archaic.txt has to be in the folder of english_synth.info
cat do-not-synthesize.txt >> filter-archaic.txt
java -cp ../$lt_tools org.languagetool.tools.SynthDictionaryBuilder -i tagger-dictionary.txt -info english_synth.info -o ../${target_dir}/english_synth.dict
cd -
mv ${target_dir}/english_synth.dict_tags.txt ${target_dir}/english_tags.txt

rm -rf tmp

#create spelling binaries
for variant in AU CA GB NZ US ZA
do
	freqlist=./spell-data/freq/en_wordlist.xml
	if [ "$variant" = "GB" ]; then
		freqlist=./spell-data/freq/en_gb_wordlist.xml
	fi
	if [ "$variant" = "US" ]; then
		freqlist=./spell-data/freq/en_us_wordlist.xml
	fi
	echo "${variant} ${freqlist}"
	cp ./info-files/en_${variant}.info ${target_dir}/hunspell/en_${variant}.info
	java -cp $lt_tools org.languagetool.tools.SpellDictionaryBuilder -i ./src-dict/output/en_${variant}.txt -freq ${freqlist} -info ${target_dir}/hunspell/en_${variant}.info -o ${target_dir}/hunspell/en_${variant}.dict
done

mvn install