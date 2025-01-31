
dic = {}
countries = ["AU", "CA", "GB", "NZ", "US", "ZA"]
for country in countries:
    dic[country]=[]
    with open("en_"+country+".txt", "r") as file:
        for line in file.readlines():
            word = line.strip().split("\t")[1]
            dic[country].append(word)
    #print (len(dic[country]))

def intersect_lists(*lists):
    return list(set(lists[0]).intersection(*lists[1:]))

common_words = intersect_lists(dic["AU"], dic["CA"], dic["GB"], dic["NZ"], dic["US"], dic["ZA"] )
#print (len(common_words))

with open("en_ALL.txt", "w") as outputfile:
    for word in sorted(common_words):
        outputfile.write(word+"\n")

for country in countries:
    with open("en_"+country+".txt", "w") as outputfile:
        for word in sorted(list(set(dic[country]) - set(common_words))):
            outputfile.write(word+"\n")