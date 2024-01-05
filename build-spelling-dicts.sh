#!/bin/bash

lt_version=6.4-SNAPSHOT
lt_tools=../languagetool/languagetool-standalone/target/LanguageTool-${lt_version}/LanguageTool-${lt_version}/languagetool.jar

#to be updated
#src_dict=./original-files-december-2023
src_dict=../languagetool/languagetool-language-modules/en/src/main/resources/org/languagetool/resource/en/hunspell

rm -rf spell-dicts
mkdir spell-dicts

for variant in AU CA GB NZ US ZA
do
	# dump the dictionaries
	java -cp $lt_tools org.languagetool.tools.DictionaryExporter -i $src_dict/en_${variant}.dict -o ./spell-dicts/en_${variant}.txt -info $src_dict/en_${variant}.info
done

# data from GB Hunspell
unmunch ./spell-data/hunspell/en-GB.dic ./spell-data/hunspell/en-GB.aff | sed 's/\t.*//' | sed 's/.*''s$//' | sed '/^$/d' >> ./spell-dicts/en_GB.txt

#convert en_NZ to utf-8
iconv -f ISO-8859-1 -t UTF-8 ./spell-dicts/en_NZ.txt | sed 's/ \+$//' | sed '/^$/d' > ./spell-dicts/en_NZ-utf8.txt
mv ./spell-dicts/en_NZ-utf8.txt ./spell-dicts/en_NZ.txt

echo "prepare prohibit.txt"
cat $src_dict/prohibit.txt | sed 's/#.*//' | sed 's/ \+$//' | sed '/^$/d' > ./spell-dicts/prohibit.txt
export LC_ALL=C && sort -u -o ./spell-dicts/prohibit.txt ./spell-dicts/prohibit.txt

for variant in AU CA GB NZ US ZA
do
	echo "${variant}"
	sed -i 's/^.\t//' ./spell-dicts/en_${variant}.txt
	cat $src_dict/spelling.txt | sed 's/#.*//' | sed 's/ \+$//' | sed '/^$/d' >> ./spell-dicts/en_${variant}.txt
	cat $src_dict/spelling_merged.txt | sed 's/#.*//' | sed 's/ \+$//' | sed '/^$/d' >> ./spell-dicts/en_${variant}.txt
	cat $src_dict/spelling_en-${variant}.txt | sed 's/#.*//' | sed 's/ \+$//' | sed '/^$/d' >> ./spell-dicts/en_${variant}.txt
	export LC_ALL=C && sort -u -o ./spell-dicts/en_${variant}.txt ./spell-dicts/en_${variant}.txt 
	comm -23 ./spell-dicts/en_${variant}.txt ./spell-dicts/prohibit.txt > ./spell-dicts/en_${variant}-prohibit.txt
	mv ./spell-dicts/en_${variant}-prohibit.txt ./spell-dicts/en_${variant}.txt
done


target_dir=src/main/resources/org/languagetool/resource/en/hunspell


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
	java -cp $lt_tools org.languagetool.tools.SpellDictionaryBuilder -i ./spell-dicts/en_${variant}.txt -freq ${freqlist} -info ${target_dir}/en_${variant}.info -o ${target_dir}/en_${variant}.dict
done





