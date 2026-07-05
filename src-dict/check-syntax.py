"""
Syntax validation module for English dictionary entries.

This module provides functionality to validate the syntax and structure of dictionary 
entries stored in text files. Each entry is expected to follow the format:
    lemma[|alternate]=POS_TAGS=variants

Key Functions:
    clean_line() - Removes comments and whitespace from input lines
    check_line() - Validates an individual dictionary entry line

Dependencies:
    inflection - Used for handling word inflections and variants

The validation includes checks for:
- Correct number of fields (lemma, tags, variants)
- Valid part-of-speech tags
- Consistency between lemmas and their variants
- Special cases for nouns, verbs and other parts of speech
"""

import inflection


def clean_line(s):
    return s.split("#")[0].strip()


def check_line(line):
    """
    Checks the validity of a line from a text file by performing various validations
    on its structure and content. The line is expected to be in a specific format
    with three parts separated by '='. The function verifies the number of parts,
    checks for known tags and variants, and ensures the consistency between lemmas
    and variant groups. It also handles specific rules for nouns and verbs, such as
    plural forms and double consonants. If any validation fails, an error message
    is printed.

    Args:
        line (str): A line from a text file to be checked.

    Returns:
        None
    """
    to_ignore = [
        ":=:=all",
        ";=:=all",
        "$=$=all",
        "#=#=all",
        "\"=''=all",
        '"=``=all',
        "there=EX=all",
        "to=TO=all",
    ]
    problems = []
    line = clean_line(line)
    if line == "" or line in to_ignore:
        return problems
    parts = line.split("=")
    if len(parts) != 3:
        problems.append(line + " >> wrong number of characters '='")
    tags = parts[1] if len(parts) > 1 else ""
    lemmas = parts[0].split("|")
    if len(parts) < 3:
        problems.append(f"Unsufficient number of fields on line: {line}")
        return problems
    variants_groups = parts[2].split("|")
    if "," not in tags and "/" in tags:
        problems.append(line + " >> incorrect combination of commas and slashes")
    if ("," in tags or "/" in tags) and tags.count(",") != tags.count("/") - 1:
        problems.append(line + " >> incorrect combination of commas and slashes")
    if "," in tags and ("|" in lemmas or "|" in variants_groups):
        problems.append(line + " >> this line cann't have multiple lemmas or groups of variants")
    if "/" not in tags:
        if tags not in [
            "noun",
            "verb",
            "noun_U",
            "noun_UN",
            "JJ",
            "UNTAGGED",
            "NN",
            "NN:U",
            "NN:UN",
            "RB",
            "NNP",
            "NNS",
            "UH",
            "NNPS",
            "CC",
            "IN",
            "CD",
            "DT",
            "FW",
            "PRP",
            "WP",
            "WP$",
            "PRP$",
            "RBS",
            "WRB",
            "WDT",
            "RP",
            "MD",
            "RBR",
            "POS",
            "PDT",
            "abbreviation",
            "contraction",
            "symbol",
            "punctuation",
            "untagged",
            "VBD",
        ]:
            problems.append(line + " >> unknown tag")
    if len(lemmas) != len(variants_groups):
        problems.append(
            line
            + " >> number of elements in lemma doesn't much number of elements in variant"
        )
    for variants_group in variants_groups:
        variants = variants_group.split(",")
        for variant in variants:
            if variant not in [
                "none",
                "all",
                "us",
                "gb",
                "ca",
                "nz",
                "au",
                "za",
                "us-large",
            ]:
                problems.append(line + " >> unknown variant")
    if len(lemmas) != len(set(lemmas)):
        problems.append(line + " >> duplicate lemmas")
    for lemma in lemmas:
        lemma, extra = inflection.getLemmaAndExtra(lemma)
        if extra != "" and tags in ["noun", "noun_U", "noun_UN"]:
            if not extra.startswith("pl. "):
                problems.append(
                    line + " >> In nouns, please indicate plural forms [pl. xxxx,yyyy]"
                )
        if extra != "" and tags == "verb" and ";" not in extra:
            duplicate_consonant = inflection.getDuplicateConsonant(extra)
            if len(duplicate_consonant) == 0:
                problems.append(
                    line
                    + " >> In verbs, please indicate a double consonant [-ll-] or [-ll-,-l-]"
                )
            last_consonant = lemma[-1]
            for c in duplicate_consonant:
                if c != last_consonant and c != last_consonant + last_consonant:
                    problems.append(
                        line
                        + " >> In verbs, please indicate a double consonant [-ll-] or [-ll-,-l-]"
                    )
        if ";" in extra:
            extra_parts = extra.split(";")
            if len(extra_parts) != 4:
                problems.append(line + " >> Irregular verbs should have 4 forms")
            if any(s == "" for s in extra_parts):
                problems.append(line + " >> Forms in irregular verbs cannot be empty")
            inflection.parseVerbalForms(
                lemma
                + "="
                + inflection.getInflectedFormsAndTags(lemma, "verb", extra)
                + "="
                + parts[2]
            )
    return problems


def _main():
    for file_path in ["./src-dict/src-clean.txt", "./src-dict/src-pending.txt"]:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file.readlines():
                for problem in check_line(line):
                    print(problem)


if __name__ == "__main__":
    _main()
