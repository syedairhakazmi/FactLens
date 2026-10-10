"""

FactLens test battery: data only (the runner is run_factlens_tests.py).



Every case has a `truth` label saying what the REAL WORLD says, not what your

corpus happens to contain. That lets the runner grade without knowing your data:



  true          a correct claim.          FAIL if any verdict is Refuted.

  false         an incorrect claim.       FAIL if any verdict is Supported.

  mixed         true + false parts.       FAIL if the whole thing comes back Supported.

  opinion       subjective.               FAIL if it gets Supported/Refuted.

  unverifiable  future, personal, made-up, or not a claim at all. Same rule as opinion.

  junk          nonsense input.           FAIL on crash or on Supported/Refuted.

  robust        only checks it does not crash.

  time_sensitive  true yesterday, maybe not today. WARN if it gets a confident verdict.

  review        ambiguous on purpose. Always shown for manual reading.



Two kinds of problem get reported differently:

  FAIL = wrong direction or crash (Supported on a false claim, Refuted on a true one)

  WARN = coverage gap (a true claim came back Not Enough Evidence), not a bug by itself



`group` ties cases together for metamorphic checks that need no ground truth:

  "same:<name>"  every member must get the same verdict (paraphrases, formatting)

  "opp:<name>"   exactly two members, a claim and its negation: they must not both

                 come back Supported, or both Refuted

"""



CATEGORY_INFO = {

    "true_facts": ("Easy true facts",

        "Baseline recall. Refuted here = verifier or retrieval picked the wrong direction. "

        "Not Enough Evidence = coverage gap in your corpus."),

    "false_facts": ("Easy false facts",

        "Supported here is the worst bug in the project: a lie stamped true. "

        "Usually retrieval found a passage about the same topic and the verifier only checked topic overlap."),

    "numbers_dates": ("Near-miss numbers, dates, units",

        "Right entity, wrong number. BM25 and embeddings both ignore digits, so retrieval returns the right passage "

        "and a weak verifier says Supported. Also tests transposed digits (1914 vs 1941) and magnitude (33 m vs 330 m)."),

    "entity_swap": ("Wrong entity, place or person",

        "Same sentence shape, wrong name. Embeddings rate these as highly similar to the true passage, "

        "so the verifier has to do real work."),

    "negation": ("Negation, double negation, contractions",

        "Opposite-pair groups (opp:) are metamorphic: a claim and its negation must not both be Supported "

        "or both Refuted. Also catches phrase-list verifiers that only know 'does not cause'."),

    "quantifiers_modality": ("All / some / most, future and hedged claims",

        "'All vaccines are...' vs 'Some vaccines are...'. Future and modal claims ('will', 'might') "

        "cannot be verified against a static corpus and should never be Supported or Refuted."),

    "compound": ("Compound sentences and cross-sentence pronouns",

        "Decomposition, coreference and aggregation. 'mixed' cases contain a false part, so an overall "

        "Supported is a failure. Also order-swap groups: 'A and B' must behave like 'B and A'."),

    "opinions": ("Opinions, and facts that merely contain evaluative words",

        "Two bugs in one category: opinions that slip through to verification, and real facts wrongly "

        "dropped as opinions because they contain 'good', 'best', 'great' ('Exercise is good for your heart')."),

    "non_claims": ("Questions, commands, greetings",

        "Not claims at all. Should not be verified."),

    "unverifiable": ("Personal, fabricated, or unknowable",

        "Made-up entities and private facts. Correct behaviour is Not Enough Evidence, never a confident verdict. "

        "Catches an over-eager relevance gate that matches any passage."),

    "time_sensitive": ("Things that change over time",

        "Your corpus is a snapshot (FEVER is 2018-era). Offices, populations and 'latest' products drift. "

        "A confident verdict here means you are quoting stale evidence."),

    "misinformation": ("Common myths and medical claims, plus true counterparts",

        "SciFact-style territory and your project's actual purpose. Includes dangerous false claims that must never be Supported."),

    "paraphrase": ("Same fact, different wording",

        "same: groups. Verdicts must match across wordings. If they differ, retrieval is wording-sensitive "

        "(BM25 without stemming) or the verifier is phrase-based."),

    "formatting_noise": ("Caps, punctuation, whitespace, emoji, typos",

        "same: groups. Formatting must never change the verdict. Your 'VACCINE!!! CAUSES???' case came from here."),

    "unicode": ("Accents and special characters",

        "Your tokenizer keeps only a-z0-9, so 'Zurich' with a u-umlaut becomes the tokens 'z' and 'rich'. "

        "Also non-breaking and zero-width spaces."),

    "multilingual": ("Urdu, Arabic, Roman Urdu, Hindi, Chinese, French, Spanish",

        "Retrieval is English-only today (BM25 gets zero tokens, MiniLM is English). Expect Not Enough Evidence until "

        "the translation layer exists. What must NOT happen: Supported on a false claim, or a crash."),

    "ambiguity_multihop": ("Ambiguous names, multi-hop, comparisons, superlatives",

        "'Paris is a city in Texas' is TRUE. A system that retrieves Paris, France and says Refuted is making a "

        "disambiguation error. Multi-hop needs two passages, so Not Enough Evidence is expected, but Refuted on a true one is not."),

    "local_context": ("Pakistan-specific facts",

        "Your committee asked for local context. Checks coverage and whether local names tokenize and retrieve properly."),

    "harmful_claims": ("Harmful generalisations",

        "Fact-check side of the project only (the hate-speech module is Iteration 3). These must never be Supported."),

    "input_shape": ("Empty, symbols, injection strings, huge inputs",

        "Crash resistance and the relevance gate. Junk like '1889' or '@#$%' must not receive a confident verdict."),

}



CASES = []





def add(cat, truth, texts, group=None, note=""):

    if isinstance(texts, str):

        texts = [texts]

    for t in texts:

        CASES.append({"cat": cat, "truth": truth, "text": t, "group": group, "note": note})





# ---------------------------------------------------------------- true_facts

add("true_facts", "true", [

    "The Eiffel Tower is located in Paris.",

    "Water boils at 100 degrees Celsius at sea level.",

    "The Earth orbits the Sun.",

    "Barack Obama was the 44th President of the United States.",

    "Albert Einstein developed the theory of relativity.",

    "The Great Wall of China is located in China.",

    "Mount Everest is the highest mountain above sea level.",

    "The capital of France is Paris.",

    "Tokyo is the capital of Japan.",

    "William Shakespeare wrote Hamlet.",

    "DNA carries genetic information.",

    "The human heart has four chambers.",

    "Photosynthesis produces oxygen.",

    "The chemical symbol for gold is Au.",

    "Humans have 46 chromosomes.",

    "The Pacific Ocean is the largest ocean on Earth.",

    "Jupiter is the largest planet in the Solar System.",

    "The Moon orbits the Earth.",

    "Leonardo da Vinci painted the Mona Lisa.",

    "Alexander Graham Bell is credited with inventing the telephone.",

    "Cairo is the capital of Egypt.",

    "Marie Curie won a Nobel Prize.",

    "Sound travels faster in water than in air.",

    "The speed of light is approximately 300,000 kilometres per second.",

    "Penguins are flightless birds.",

])



# --------------------------------------------------------------- false_facts

add("false_facts", "false", [

    "The Eiffel Tower is located in London.",

    "Water boils at 50 degrees Celsius at sea level.",

    "The Sun orbits the Earth.",

    "Barack Obama was the 10th President of the United States.",

    "Albert Einstein invented the telephone.",

    "The Great Wall of China is located in Brazil.",

    "Mount Everest is located in Australia.",

    "The capital of France is Berlin.",

    "William Shakespeare wrote The Odyssey.",

    "The human heart has two chambers.",

    "Photosynthesis produces methane.",

    "The chemical symbol for gold is Ag.",

    "Humans have 48 chromosomes.",

    "The Atlantic Ocean is the largest ocean on Earth.",

    "Mars is the largest planet in the Solar System.",

    "The Moon is made of cheese.",

    "Leonardo da Vinci painted The Starry Night.",

    "Cairo is the capital of Turkey.",

    "Marie Curie won an Olympic gold medal.",

    "The speed of light is approximately 300 kilometres per second.",

    "Penguins can fly long distances.",

    "Sound travels faster in air than in water.",

])



# ------------------------------------------------------------- numbers_dates

add("numbers_dates", "true", [

    "World War II ended in 1945.",

    "World War I began in 1914.",

    "Apollo 11 landed on the Moon in 1969.",

    "The Titanic sank in 1912.",

    "The Eiffel Tower was completed in 1889.",

    "The Berlin Wall fell in 1989.",

    "Pakistan became independent in 1947.",

    "The Earth is about 150 million kilometres from the Sun.",

    "Water freezes at 32 degrees Fahrenheit.",

    "Water freezes at 0 degrees Celsius.",

])

add("numbers_dates", "false", [

    "World War II ended in 1944.",

    "World War I began in 1941.",

    "Apollo 11 landed on the Moon in 1959.",

    "The Titanic sank in 1921.",

    "The Eiffel Tower was completed in 1890.",

    "The Eiffel Tower was completed in 1789.",

    "The Berlin Wall fell in 1991.",

    "Pakistan became independent in 1950.",

    "The Eiffel Tower is about 33 metres tall.",

    "The Eiffel Tower is about 3,300 metres tall.",

    "The Earth is about 15 million kilometres from the Sun.",

    "Water freezes at 100 degrees Celsius.",

])

add("numbers_dates", "true", "The Eiffel Tower was completed in eighteen eighty-nine.",

    note="Number written as words. Coverage miss expected, Refuted would be a bug.")



# --------------------------------------------------------------- entity_swap

add("entity_swap", "false", [

    "Michelangelo painted the Mona Lisa.",

    "Paris is the capital of Texas.",

    "Berlin is the capital of Spain.",

    "Lima is the capital of Brazil.",

    "Isaac Newton developed the theory of general relativity.",

    "Neil Armstrong was the first person to walk on Mars.",

    "The Nile flows through Canada.",

    "Tim Burton directed The Godfather.",

    "The Beatles were from Manchester.",

    "Beethoven composed The Magic Flute.",

])

add("entity_swap", "true", [

    "The Nile flows through Egypt.",

    "Tim Burton directed Edward Scissorhands.",

    "The Beatles were from Liverpool.",

    "Mozart composed The Magic Flute.",

])



# ------------------------------------------------------------------ negation

add("negation", "true", "The Earth orbits the Sun.", group="opp:sun")

add("negation", "false", "The Earth does not orbit the Sun.", group="opp:sun")

add("negation", "false", "The Earth is flat.", group="opp:flat")

add("negation", "true", "The Earth is not flat.", group="opp:flat")

add("negation", "false", "Vaccines cause autism.", group="opp:autism")

add("negation", "true", "Vaccines do not cause autism.", group="opp:autism")

add("negation", "true", "Water boils at 100 degrees Celsius at sea level.", group="opp:boil")

add("negation", "false", "Water does not boil at 100 degrees Celsius at sea level.", group="opp:boil")

add("negation", "true", "The Eiffel Tower is located in Paris.", group="opp:eiffel")

add("negation", "false", "The Eiffel Tower is not located in Paris.", group="opp:eiffel")

add("negation", "true", "The Eiffel Tower is not located in London.",

    note="True because of the negation. A verifier that treats any 'not' as Refuted fails this.")

add("negation", "false", [

    "The Eiffel Tower isn't in Paris.",

    "Paris isn't the capital of France.",

    "Humans never landed on the Moon.",

    "No human has walked on the Moon.",

    "All birds can fly.",

    "Smoking is harmless to the lungs.",

    "It is false that the Earth is round.",

])

add("negation", "true", [

    "Paris isn't the capital of Germany.",

    "The Earth isn't flat.",

    "It is not true that the Earth is flat.",

    "It is not the case that the Eiffel Tower is not in Paris.",

    "Not all birds can fly.",

    "Penguins are unable to fly.",

    "Smoking is harmful to health.",

    "Antibiotics are ineffective against viruses.",

])



# -------------------------------------------------------- quantifiers_modality

add("quantifiers_modality", "true", [

    "Some vaccines are made from weakened viruses.",

    "Most people have two eyes.",

    "Many birds migrate south in winter.",

    "At least one planet in the Solar System has rings.",

    "Experts say smoking causes cancer.",

    "Scientists believe the universe is about 13.8 billion years old.",

])

add("quantifiers_modality", "false", [

    "All vaccines are made from weakened viruses.",

    "Every country in Africa is landlocked.",

    "No planet in the Solar System has rings.",

    "Everyone in Pakistan speaks Urdu as a first language.",

    "All mammals lay eggs.",

])

add("quantifiers_modality", "unverifiable", [

    "The Eiffel Tower will be demolished in 2030.",

    "It will rain in Lahore tomorrow.",

    "Bitcoin will reach one million dollars next year.",

    "Humans might live on Mars by 2050.",

    "It is possible that life exists on other planets.",

    "The Eiffel Tower could be moved to London.",

])

add("quantifiers_modality", "review", "Some people claim the Moon landing was faked.",

    note="True that people claim it. A system may Refute the embedded claim instead.")



# ------------------------------------------------------------------ compound

add("compound", "true", [

    "The Eiffel Tower is in Paris and it was completed in 1889.",

    "Water boils at 100 degrees Celsius and freezes at 0 degrees Celsius.",

    "Tokyo is in Japan, Cairo is in Egypt, and Paris is in France.",

    "Einstein was born in Germany, and he won the Nobel Prize in Physics.",

    "The Eiffel Tower was completed in 1889. It is located in Paris.",

    "Marie Curie was born in Poland. She won two Nobel Prizes.",

    "Apples, oranges, and bananas are fruits.",

    "The Moon orbits the Earth, and the Earth orbits the Sun.",

    "Napoleon was born in Corsica. He became Emperor of the French. He died on Saint Helena.",

    "The Eiffel Tower is in Paris, Paris is in France, France is in Europe, and Europe is a continent.",

])

add("compound", "mixed", [

    "The Eiffel Tower is in London and it was completed in 1889.",

    "Paris is the capital of France, and Berlin is the capital of Spain.",

    "Water boils at 100 degrees Celsius and freezes at 50 degrees Celsius.",

    "Tokyo is in Japan, Cairo is in Egypt, and Lima is in Brazil.",

    "Einstein was born in France, and he won the Nobel Prize in Physics.",

    "The Eiffel Tower was completed in 1889. It is located in Rome.",

    "Marie Curie was born in Poland. She won three Nobel Prizes.",

    "Penguins live in Antarctica. They can fly.",

    "Although the Eiffel Tower is in Paris, it is not in France.",

    "The vaccine was approved last week, and it causes infertility, and the Eiffel Tower is in Paris.",

    "Mount Everest is the highest mountain and it is located in Australia.",

    "The Sun is a star and the Moon is a star.",

    "Paris is in France; Berlin is in Italy.",

    "The Eiffel Tower is in Paris, Paris is in France, France is in Europe, and Europe is in Asia.",

    "The Eiffel Tower is in Paris.\nParis is in Germany.",

    "1. The Eiffel Tower is in Paris.\n2. Berlin is in Spain.",

], note="Contains a false part, so an overall Supported is wrong.")

add("compound", "mixed", "The Eiffel Tower is in Paris and it was completed in 1950.", group="same:order1")

add("compound", "mixed", "The Eiffel Tower was completed in 1950 and it is in Paris.", group="same:order1")

add("compound", "mixed", "Paris is the capital of France, and Berlin is the capital of Spain.", group="same:order2")

add("compound", "mixed", "Berlin is the capital of Spain, and Paris is the capital of France.", group="same:order2")

add("compound", "false", "The Eiffel Tower is in London and it was completed in 1950.")

add("compound", "unverifiable", [

    "Alice thanked Maria because she had helped her.",

    "The trophy did not fit in the suitcase because it was too big.",

], note="Genuinely ambiguous pronouns. Coreference should not invent certainty.")



# ------------------------------------------------------------------- opinions

add("opinions", "opinion", [

    "The Eiffel Tower is beautiful.",

    "Paris is the best city in the world.",

    "This woman is evil.",

    "Pineapple on pizza is disgusting.",

    "Cats are better than dogs.",

    "The movie was terrible.",

    "He is a good boy.",

    "What a wonderful day!",

    "In my opinion the vaccine is dangerous.",

    "I think the Earth is flat.",

    "I believe Paris is overrated.",

    "Everyone knows Paris is the most romantic city.",

    "She is the worst teacher ever.",

    "That was an awful decision.",

    "What a terrible idea.",

    "Honestly, the food here is amazing.",

    "Mozart is overrated.",

    "Pakistan has the most beautiful mountains.",

], note="Several of these dodge the copula pattern on purpose ('What a terrible idea', 'has the most beautiful').")

add("opinions", "true", [

    "Mount Everest is the highest mountain on Earth.",

    "Jupiter is the largest planet in the Solar System.",

    "The Nile is the longest river in Africa.",

    "Exercise is good for your heart.",

    "Smoking is bad for your health.",

    "The Great Barrier Reef is the largest coral reef system in the world.",

    "The Eiffel Tower is the tallest structure in Paris.",

    "Vitamin C is important for the immune system.",

], note="Facts with evaluative or superlative words. Wrongly dropped as 'opinion' counts as a coverage miss.")



# ----------------------------------------------------------------- non_claims

add("non_claims", "unverifiable", [

    "Is the Eiffel Tower in Paris?",

    "Who built the Eiffel Tower?",

    "Visit the Eiffel Tower!",

    "Hello!",

    "Thanks.",

    "Please check this for me.",

    "Lol.",

    "OK.",

], note="Not claims. Rewriting a question into a claim is a design choice, but it should be deliberate.")



# --------------------------------------------------------------- unverifiable

add("unverifiable", "unverifiable", [

    "I ate cereal this morning.",

    "My neighbour has a red car.",

    "Zxqv Incorporated was founded in 1999.",

    "The Eiffel Tower is located in the city of Zorblax.",

    "Dr. Plimpton Vask discovered the element glorpium.",

    "The village of Fakeville has a population of 4,213.",

    "Quantum computers broke RSA encryption in 2025.",

    "A newly announced phone this year shipped with a graphene-based battery.",

    "The company announced record profits yesterday.",

])



# -------------------------------------------------------------- time_sensitive

add("time_sensitive", "time_sensitive", [

    "Joe Biden is the current President of the United States.",

    "The current Prime Minister of the United Kingdom is Boris Johnson.",

    "The latest iPhone is the iPhone 12.",

    "The world population is 7 billion.",

    "Bitcoin is worth ten thousand dollars.",

])

add("time_sensitive", "true", "The 2018 FIFA World Cup was held in Russia.")

add("time_sensitive", "false", "The 2022 FIFA World Cup was won by Brazil.")



# ------------------------------------------------------------ misinformation

add("misinformation", "false", [

    "The Moon landing was faked.",

    "The Earth is 6,000 years old.",

    "5G towers spread COVID-19.",

    "Vaccines contain microchips.",

    "Drinking bleach cures COVID-19.",

    "Humans use only 10 percent of their brains.",

    "Lightning never strikes the same place twice.",

    "Goldfish have a three-second memory.",

    "Bats are blind.",

    "Vikings wore horned helmets.",

    "Antibiotics cure viral infections.",

    "Garlic cures COVID-19.",

    "Eating carrots gives you night vision.",

    "The Great Wall of China is visible from space with the naked eye.",

    "Sugar makes children hyperactive.",

    "Cracking your knuckles causes arthritis.",

])

add("misinformation", "true", [

    "Smoking causes lung cancer.",

    "Antibiotics are used to treat bacterial infections.",

    "Insulin is used to treat diabetes.",

    "Vitamin D deficiency can cause rickets.",

    "The COVID-19 vaccine does not cause infertility.",

    "Vaccines are safe for pregnant women.",

    "Handwashing reduces the spread of infections.",

    "Aspirin can thin the blood.",

    "Smallpox was eradicated through vaccination.",

    "Polio is caused by a virus.",

    "Malaria is transmitted by mosquitoes.",

    "Tuberculosis is caused by bacteria.",

    "Penicillin was discovered by Alexander Fleming.",

])



# ----------------------------------------------------------------- paraphrase

add("paraphrase", "true", [

    "The Eiffel Tower was completed in 1889.",

    "The Eiffel Tower was finished in 1889.",

    "Construction of the Eiffel Tower ended in 1889.",

    "In 1889, the Eiffel Tower was completed.",

    "1889 was the year the Eiffel Tower was completed.",

    "Gustave Eiffel's company completed the Eiffel Tower in 1889.",

], group="same:eiffel1889")

add("paraphrase", "true", [

    "The Eiffel Tower was built by Gustave Eiffel's company.",

    "Gustave Eiffel's company built the Eiffel Tower.",

    "The Eiffel Tower was constructed by Gustave Eiffel's company.",

], group="same:eiffelbuilder")

add("paraphrase", "true", [

    "The COVID-19 vaccine does not cause infertility.",

    "COVID-19 vaccination has no effect on fertility.",

    "There is no link between the COVID-19 vaccine and infertility.",

    "Getting the COVID-19 vaccine will not make you infertile.",

], group="same:vaxfert-true")

add("paraphrase", "false", [

    "The COVID-19 vaccine causes infertility.",

    "COVID-19 vaccination makes people infertile.",

    "Immunization shots can leave people unable to have children.",

    "The jab causes infertility.",

    "The vacine causes infertilty.",

], group="same:vaxfert-false")

add("paraphrase", "true", [

    "Paris is the capital of France.",

    "The capital city of France is Paris.",

    "France's capital is Paris.",

    "Paris serves as the capital of France.",

], group="same:capital")

add("paraphrase", "true", [

    "The COVID jab was cleared by regulators.",

    "The COVID-19 vaccine was approved by regulators.",

    "Regulators approved the COVID-19 vaccine.",

], group="same:jab")



# ---------------------------------------------------------- formatting_noise

add("formatting_noise", "true", [

    "The Eiffel Tower is located in Paris.",

    "the eiffel tower is located in paris",

    "THE EIFFEL TOWER IS LOCATED IN PARIS",

    "THE EIFFEL TOWER IS LOCATED IN PARIS!!!",

    "The   Eiffel     Tower   is located in   Paris.",

    "The Eiffel Tower is located in Paris",

    "The Eiffel Tower is located in Paris...",

    "  The Eiffel Tower is located in Paris.  ",

    "\tThe Eiffel Tower is located in Paris.\n",

    "The Eiffel Tower is located in Paris. \U0001F5FC\U0001F1EB\U0001F1F7",

    "The Eiffel Tower is located in Paris #travel https://example.com",

    "**The Eiffel Tower** is located in _Paris_.",

    "'The Eiffel Tower is located in Paris.'",

    "\"The Eiffel Tower is located in Paris.\"",

    "The Eiffel Tower, is located, in Paris.",

    "eiffel tower is in paris lol",

    "The Eifel Tower is located in Paris.",

    "Teh Eiffel Tower is located in Paris.",

    "The Eiffel Towr is located in Paris.",

    "The Eiffel Tower is lcoated in Paris.",

], group="same:fmt-paris")

add("formatting_noise", "false", [

    "The Eiffel Tower is located in London.",

    "the eiffel tower is located in london",

    "THE EIFFEL TOWER IS LOCATED IN LONDON!!!",

    "The   Eiffel     Tower   is located in   London.",

    "eiffel tower is in london lol",

    "The Eifel Tower is located in London.",

], group="same:fmt-london")

add("formatting_noise", "false", "VACCINE!!! CAUSES??? INFERTILITY...",

    note="Your own earlier test. Now normalised, should be Refuted or NEI, never Supported.")



# ------------------------------------------------------------------- unicode

add("unicode", "true", [

    "Z\u00fcrich is the largest city in Switzerland.",

    "S\u00e3o Paulo is a city in Brazil.",

    "Gda\u0144sk is a city in Poland.",

    "Beyonc\u00e9 was born in Houston, Texas.",

    "Reykjav\u00edk is the capital of Iceland.",

    "Krak\u00f3w is a city in Poland.",

    "The Eiffel Tower \u2014 a wrought-iron lattice tower \u2014 is in Paris.",

    "The\u00a0Eiffel\u00a0Tower is located in Paris.",

    "The Eiffel\u200b Tower is located in Paris.",

], note="Non-ASCII letters are dropped by the a-z0-9 tokenizer, splitting words into fragments.")

add("unicode", "false", "Z\u00fcrich is the capital of Switzerland.")



# -------------------------------------------------------------- multilingual

add("multilingual", "true", [

    "\u0627\u06cc\u0641\u0644 \u0679\u0627\u0648\u0631 \u067e\u06cc\u0631\u0633 \u0645\u06cc\u06ba \u0648\u0627\u0642\u0639 \u06c1\u06d2\u06d4",

    "\u0627\u0633\u0644\u0627\u0645 \u0622\u0628\u0627\u062f \u067e\u0627\u06a9\u0633\u062a\u0627\u0646 \u06a9\u0627 \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u06c1\u06d2\u06d4",

    "\u0628\u0631\u062c \u0625\u064a\u0641\u0644 \u064a\u0642\u0639 \u0641\u064a \u0628\u0627\u0631\u064a\u0633.",

    "\u0627\u0644\u0642\u0627\u0647\u0631\u0629 \u0647\u064a \u0639\u0627\u0635\u0645\u0629 \u0645\u0635\u0631.",

    "Eiffel Tower Paris mein hai.",

    "Islamabad Pakistan ka darulhukumat hai.",

    "\u090f\u092b\u093f\u0932 \u091f\u0949\u0935\u0930 \u092a\u0947\u0930\u093f\u0938 \u092e\u0947\u0902 \u0939\u0948\u0964",

    "\u57c3\u83f2\u5c14\u94c1\u5854\u4f4d\u4e8e\u5df4\u9ece\u3002",

    "La tour Eiffel est situ\u00e9e \u00e0 Paris.",

    "Eiffel Tower Paris mein hai, and it was completed in 1889.",

], note="Expect Not Enough Evidence until translation exists. Refuted would be a bug.")

add("multilingual", "false", [

    "\u0627\u06cc\u0641\u0644 \u0679\u0627\u0648\u0631 \u0644\u0646\u062f\u0646 \u0645\u06cc\u06ba \u0648\u0627\u0642\u0639 \u06c1\u06d2\u06d4",

    "\u06a9\u0631\u0627\u0686\u06cc \u067e\u0627\u06a9\u0633\u062a\u0627\u0646 \u06a9\u0627 \u062f\u0627\u0631\u0627\u0644\u062d\u06a9\u0648\u0645\u062a \u06c1\u06d2\u06d4",

    "\u0628\u0631\u062c \u0625\u064a\u0641\u0644 \u064a\u0642\u0639 \u0641\u064a \u0644\u0646\u062f\u0646.",

    "\u0627\u0644\u0642\u0627\u0647\u0631\u0629 \u0647\u064a \u0639\u0627\u0635\u0645\u0629 \u062a\u0631\u0643\u064a\u0627.",

    "Eiffel Tower London mein hai.",

    "Karachi Pakistan ka darulhukumat hai.",

    "La Torre Eiffel est\u00e1 en Londres.",

    "\u0648\u06cc\u06a9\u0633\u06cc\u0646 \u0628\u0627\u0646\u062c\u06be \u067e\u0646 \u06a9\u0627 \u0633\u0628\u0628 \u0628\u0646\u062a\u06cc \u06c1\u06d2\u06d4",

], note="Semantic matching on foreign text can latch onto the TRUE passage and say Supported. That is the bug to look for.")

add("multilingual", "opinion", [

    "Ye aurat buri hai.",

    "\u06cc\u06c1 \u0639\u0648\u0631\u062a \u0628\u0631\u06cc \u06c1\u06d2\u06d4",

])



# ------------------------------------------------------- ambiguity_multihop

add("ambiguity_multihop", "true", [

    "Paris is a city in Texas.",

    "Mercury is the closest planet to the Sun.",

    "Mercury is a metal that is liquid at room temperature.",

    "Georgia is a country in the Caucasus.",

    "Georgia is a state in the United States.",

    "Washington is the capital of the United States.",

    "Java is an island in Indonesia.",

    "Python is a type of snake.",

], note="Both meanings are true. Refuted means the system picked one sense and ignored the other.")

add("ambiguity_multihop", "true", [

    "The director of Titanic also directed Avatar.",

    "The capital of the country where the Eiffel Tower is located is Paris.",

    "The author of Hamlet was born in Stratford-upon-Avon.",

    "Tokyo has a larger population than Paris.",

    "Mount Everest is taller than K2.",

    "Russia is larger than Canada by area.",

], note="Needs two facts. Not Enough Evidence is acceptable, Refuted is not.")

add("ambiguity_multihop", "false", [

    "The author of Harry Potter was born in Scotland.",

    "The director of Titanic also directed The Godfather.",

    "The president who signed the Civil Rights Act of 1964 was Abraham Lincoln.",

    "Paris has a larger population than Tokyo.",

    "K2 is taller than Mount Everest.",

    "Canada is larger than Russia by area.",

    "K2 is the tallest mountain on Earth.",

    "The Amazon is the shortest river in the world.",

])



# ------------------------------------------------------------- local_context

add("local_context", "true", [

    "Islamabad is the capital of Pakistan.",

    "Pakistan became independent in 1947.",

    "Lahore is the capital of Punjab province.",

    "Karachi is the capital of Sindh province.",

    "Quetta is the capital of Balochistan province.",

    "Peshawar is the capital of Khyber Pakhtunkhwa.",

    "Muhammad Ali Jinnah was the founder of Pakistan.",

    "The Indus River flows through Pakistan.",

    "Urdu is the national language of Pakistan.",

    "K2 is located in the Karakoram range.",

    "Allama Iqbal is the national poet of Pakistan.",

])

add("local_context", "false", [

    "Karachi is the capital of Pakistan.",

    "Allama Iqbal was the first Prime Minister of Pakistan.",

    "The Indus River flows through Brazil.",

    "Lahore is the capital of Balochistan province.",

    "The national language of Pakistan is Arabic.",

    "Islamabad is located in Sindh province.",

])



# ------------------------------------------------------------ harmful_claims

add("harmful_claims", "false", [

    "All immigrants are criminals.",

    "All politicians are corrupt.",

    "People from that country are all criminals and should be thrown out.",

    "Women are worse at mathematics than men.",

])



# --------------------------------------------------------------- input_shape

add("input_shape", "junk", [

    "", " ", "\n\n\t", ".", "?", "!!!", "...", "a", "the", "It is.",

    "123", "1889", "2025-10-10", "@#$%^&*()", "\U0001F600\U0001F600\U0001F600",

    "null", "NaN", "undefined",

    "Paris Paris Paris Paris Paris Paris Paris Paris",

    "Eiffel Tower Paris France 1889 capital vaccine infertility Texas moon",

])

add("input_shape", "robust", [

    "<script>alert(1)</script>",

    "'; DROP TABLE users; --",

    "{{7*7}}",

    "${jndi:ldap://x}",

    "../../etc/passwd",

    "\u0000",

    "&lt;b&gt;Paris&lt;/b&gt;",

    '{"claim": "The Eiffel Tower is in Paris"}',

    "a" * 5000,

])

add("input_shape", "true", [

    "<p>The Eiffel Tower is located in Paris.</p>",

    "The Eiffel Tower is located in Paris.\r\nParis is located in France.",

    "The Eiffel Tower is located in Paris. " * 400,

], note="Markup, Windows newlines, and a 12,000-character repeat. Must not crash, must not be Refuted.")

add("input_shape", "robust",

    " ".join(["The Eiffel Tower is located in Paris and Paris is the capital of France."] * 100),

    note="About 1,500 words. Check latency, not the verdict.")



# ---------------------------------------------------------------- API checks

# (name, method, path, body, content_type, ok_statuses). Anything 5xx is a failure regardless.

ENDPOINT_CASES = [

    ("health endpoint", "GET", "/api/health", None, None, {200}),

    ("GET on analyze (wrong method)", "GET", "/api/analyze", None, None, {405, 422}),

    ("unknown path", "GET", "/api/nope", None, None, {404}),

    ("missing text field", "POST", "/api/analyze", "{}", "application/json", {422}),

    ("null text", "POST", "/api/analyze", '{"text": null}', "application/json", {422, 200}),

    ("numeric text", "POST", "/api/analyze", '{"text": 123}', "application/json", {422, 200}),

    ("array text", "POST", "/api/analyze", '{"text": ["a", "b"]}', "application/json", {422}),

    ("object text", "POST", "/api/analyze", '{"text": {}}', "application/json", {422}),

    ("wrong field name", "POST", "/api/analyze", '{"claim": "The Eiffel Tower is in Paris."}', "application/json", {422}),

    ("not JSON at all", "POST", "/api/analyze", "hello", "text/plain", {422, 415}),

    ("broken JSON", "POST", "/api/analyze", '{"text": ', "application/json", {422, 400}),

    ("extra unknown fields", "POST", "/api/analyze", '{"text": "The Eiffel Tower is in Paris.", "foo": 1}', "application/json", {200}),

    ("escaped null byte", "POST", "/api/analyze", '{"text": "\\u0000"}', "application/json", {200, 422}),

    ("2 MB payload", "POST", "/api/analyze", '{"text": "' + ("The Eiffel Tower is in Paris. " * 70000) + '"}', "application/json", {200, 413, 422}),

]
