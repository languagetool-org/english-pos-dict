## Goal

This project provides a unique [source file](https://github.com/languagetool-org/english-pos-dict/blob/main/src-dict/src-clean.txt) and a set of scripts to maintain an English dictionary. From this source file, we will generate the tagger dictionary and the spelling dictionaries (for different variants: US, GB, CA, AU, NZ, SZ) used in LanguageTool. 

## Required knowledge

Maintainers of the dictionary should be familiar with the tagging set used in LanguageTool (see the [tagset info](https://github.com/languagetool-org/languagetool/blob/master/languagetool-language-modules/en/src/main/resources/org/languagetool/resource/en/tagset.txt))

## Format 

The general format of dictionary entries is:
```
lemma=forms_and_tags=variants
```

Generally, we can write all forms of a lemma this way:
```
be=be/VB,was/VBD,wast/VBD,were/VBD,being/VBG,been/VBN,'m/VBP,'re/VBP,am/VBP,are/VBP,'s/VBZ,is/VBZ=all
```
If there is only one form for a lemma, and form and lemma are the same:
```
beautiful=JJ=all
beautifully=RB=all
beautifulness=NN:U=all
```
### Variants
Variants can be any of `us,gb,ca,au,nz,za` (comma-separated). `all` and `none` are used as shorthands for all variants or none (unclassified words).

If there are different spellings of a lemma for different variants, we can write them in the same line separated by the character `|`:

```
unrealizable|unrealisable=JJ=us,ca,gb|gb,au,nz,za
unrealized|unrealised=JJ=us,ca,gb|gb,au,nz,za
unrealize|unrealise=verb=us,ca,gb|gb,au,nz,za
```
The number of elements in the lemma separated by `|` must be equal to the number of groups in the variants. In the first example `unrealizable` will be used in variants `us,ca,gb` and `unrealisable` will be used in variants `gb,au,nz,za`.

### Nouns
To make it easier to write nouns, we use the shorthands `noun`, `noun_U` and `noun_UN`. In these cases, there will be a regular plural form generated automatically.

* `bicycle=noun=all` is equivalent to `bicycle=bicycle/NN,bicycles/NNS=all`
* `bidding=noun_U=all` is equivalent to `bidding=bidding/NN:U,biddings/NNS=all`
* `bind=noun_UN=all` is equivalent to `bind=bind/NN:UN,binds/NNS=all`

Irregular plurals (one or more) can be written this way:
```
nightwatchman [pl. nightwatchmen]=noun=all
sportsperson [pl. sportspersons,sportspeople]=noun=all
sister-in-law [pl. sisters-in-law]=noun=all
```

### Verbs
Regular verbs can be written this way:
```
spot=verb=all
sprawl=verb=all
spray=verb=all
```
In case a double consonant (or double and single consonant) is needed, use:
```
submit [-tt-]=verb=all
unfocus [-ss-,-s-]=verb=all
```
Irregular verbs can be written, with [third_person,past,past_participle,ing_form]:
```
sing [sings;sang;sung;singing]=verb=all
hide [hides;hid;hid,hidden;hiding]=verb=all
```
### Adjectives

```
happy-go-lucky=JJ=all
happy=happy/JJ,happier/JJR,happiest/JJS=all
```

## Scripts
* Script to make tests
* Script to build the dictionaries

