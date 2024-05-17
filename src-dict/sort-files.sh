for file in src-pending.txt src-clean.txt
do
	export LC_ALL=C && sort -u $file -o $file
done