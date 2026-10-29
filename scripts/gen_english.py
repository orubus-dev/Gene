#!/usr/bin/env python3
"""Teacher-side generator — the big English lesson packs.

This is the TEACHER's data (the same channel as every curriculum pack:
structured lessons digested through observe/inherit — never written into
the organism as answers). It writes:

  curriculum/taxonomy-1.json   the living world: spine + ~340 creatures/plants
  curriculum/taxonomy-2.json   the made world: ~470 objects/places/people
  curriculum/vocab-verbs.json  ~300 verbs with all forms (irregulars explicit)
  curriculum/vocab-adj.json    ~250 adjectives + adverbs
  curriculum/sent-grammar.json function words, aux tables, contractions,
                               patterns, punctuation + the grammar-type roster

Line format for entity blocks:  word|parent|key:value|key:value|...
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gene.dsl import reg_past, reg_ing, reg_third  # noqa: E402

CURR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "curriculum")

IRREG_NOUNS = {
    "man": "men", "woman": "women", "child": "children", "foot": "feet",
    "tooth": "teeth", "mouse": "mice", "person": "people", "leaf": "leaves",
    "knife": "knives", "wife": "wives", "life": "lives", "wolf": "wolves",
    "shelf": "shelves", "calf": "calves", "half": "halves", "loaf": "loaves",
    "thief": "thieves", "city": "cities", "baby": "babies", "lady": "ladies",
    "story": "stories", "party": "parties", "family": "families",
    "puppy": "puppies", "pony": "ponies", "sky": "skies", "box": "boxes",
    "bus": "buses", "kiss": "kisses", "watch": "watches", "dish": "dishes",
    "fox": "foxes", "bush": "bushes", "glass": "glasses", "fish": "fish",
    "sheep": "sheep", "deer": "deer", "moose": "moose", "series": "series",
    "species": "species", "aircraft": "aircraft", "potato": "potatoes",
    "tomato": "tomatoes", "hero": "heroes", "echo": "echoes",
    "piano": "pianos", "photo": "photos", "goose": "geese", "ox": "oxen",
    "die": "dice", "cactus": "cacti", "fungus": "fungi", "axis": "axes",
}


def plural(w):
    if w in IRREG_NOUNS:
        return IRREG_NOUNS[w]
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith("fe"):
        return w[:-2] + "ves"
    if w.endswith("f") and w not in ("roof", "chief", "belief"):
        return w[:-1] + "ves"
    return w + "s"


def entity_concepts(block, kind="entity", extra_words=None):
    """Parse word|parent|k:v|... lines into curriculum concepts."""
    out = []
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        word = parts[0]
        parent = parts[1] if len(parts) > 1 and parts[1] else None
        attrs = {}
        words = [word] + (extra_words or [])
        for kv in parts[2:]:
            if ":" in kv:
                k, v = kv.split(":", 1)
                attrs[k.strip()] = v.strip()
        if word not in ("fish", "sheep", "deer", "moose", "series", "species"):
            attrs.setdefault("plural", plural(word))
        cid = word.replace(" ", "_")
        for w in words:
            if " " in w:
                pass  # multiword bindings fine
        c = {"id": cid, "kind": kind, "words": list(dict.fromkeys(words)),
             "attrs": attrs}
        if parent:
            c["relations"] = [{"to": parent, "rel": "is-a"}]
        out.append(c)
    return out


def cat(cid, words, definition, parent=None):
    c = {"id": cid, "kind": "category",
         "words": words if isinstance(words, list) else [words],
         "attrs": {"def": definition}}
    if parent:
        c["relations"] = [{"to": parent, "rel": "is-a"}]
    return c


# ============================ TAXONOMY 1 — the living world ===================
SPINE = [
    cat("entity", ["entity", "thing"], "anything that exists — a thing, a living being, a place or an idea"),
    cat("living", ["living", "living thing", "life"], "something alive — it grows, reproduces and needs energy", "entity"),
    cat("organism", ["organism"], "a living thing", "living"),
    cat("animal", ["animal", "creature"], "a living thing that moves and eats other living things", "organism"),
    cat("vertebrate", ["vertebrate"], "an animal with a backbone", "animal"),
    cat("invertebrate", ["invertebrate"], "an animal without a backbone", "animal"),
    cat("mammal", ["mammal", "mammals"], "a warm-blooded animal that nurses its young", "vertebrate"),
    cat("bird", ["bird"], "an animal with feathers, a beak and two wings", "vertebrate"),
    cat("fish_cat", ["fish"], "an animal that lives in water and breathes through gills", "vertebrate"),
    cat("reptile", ["reptile"], "a cold-blooded animal with scaly skin", "vertebrate"),
    cat("amphibian", ["amphibian"], "a soft-skinned animal that lives both in water and on land", "vertebrate"),
    cat("insect", ["insect", "bug"], "a tiny animal with six legs and a three-part body", "invertebrate"),
    cat("arachnid", ["arachnid"], "an animal with eight legs and an exoskeleton", "invertebrate"),
    cat("crustacean", ["crustacean"], "a mostly-water animal with a hard shell and many legs", "invertebrate"),
    cat("mollusk", ["mollusk"], "a soft-bodied animal, often inside a shell", "invertebrate"),
    cat("plant", ["plant"], "a living thing that makes its food from sunlight", "organism"),
    cat("tree_cat", ["tree"], "a tall plant with a woody trunk", "plant"),
    cat("flower_cat", ["flower", "blossom"], "a blossoming plant", "plant"),
    cat("fungus", ["fungus", "fungi"], "a living thing that feeds on decay, like a mushroom", "organism"),
    cat("microbe", ["microbe", "microorganism"], "a living thing too small to see", "organism"),
    cat("mythical_cat", ["mythical creature"], "a creature from stories and legends, not nature", "idea"),
    cat("canid", ["canid", "dog family"], "a dog-family mammal — it hunts or was tamed from hunters", "mammal"),
    cat("felid", ["felid", "cat family"], "a cat-family mammal — a stealthy hunter with sharp claws", "mammal"),
    cat("ursid", ["ursid", "bear family"], "a bear-family mammal — big, strong and heavyset", "mammal"),
    cat("equine", ["equine", "horse family"], "a horse-family mammal — built for running on open land", "mammal"),
    cat("bovine", ["bovine", "cattle family"], "a cattle-family mammal — hoofed and grass-eating", "mammal"),
    cat("rodent", ["rodent"], "a gnawing mammal with big front teeth", "mammal"),
    cat("primate", ["primate"], "an ape-family mammal with grasping hands", "mammal"),
    cat("marsupial", ["marsupial"], "a mammal that carries its young in a pouch", "mammal"),
    cat("cetacean", ["cetacean", "whale family"], "a whale-family mammal that lives its whole life in the sea", "mammal"),
    cat("ungulate", ["ungulate", "hoofed mammal"], "a hoofed, plant-eating mammal", "mammal"),
]

ANIMALS = """
dog|canid|sound:barks|diet:meat and kibble|role:a loyal pet|feature:wags its tail when happy
cat|felid|sound:purrs|diet:meat and fish|role:an independent pet|feature:whiskers and slit eyes
horse|equine|sound:neighs|diet:grass and hay|role:rides and pulls loads|feature:runs fast
cow|bovine|sound:moos|diet:grass|role:gives milk|feature:chews cud
pig|ungulate|sound:oinks|diet:almost anything|role:farm animal|feature:smart and rootless nose
sheep|bovine|sound:baas|diet:grass|role:gives wool|feature:thick fleece
goat|bovine|sound:bleats|diet:grass and shrubs|role:gives milk|feature:climbs almost anything
lion|felid|sound:roars|diet:zebra and antelope|habitat:african grasslands|feature:the male's mane
tiger|felid|sound:growls|diet:deer and wild pigs|habitat:asian forests|feature:orange striped coat
bear|ursid|sound:growls|diet:fish, berries and honey|habitat:forests|feature:hibernates all winter
wolf|canid|sound:howls|diet:deer and elk|habitat:wild forests|feature:hunts in packs
fox|canid|sound:barks|diet:rodents and berries|habitat:woodland edges|feature:bushy red tail
elephant|proboscidean|sound:trumpets|diet:leaves and fruit|habitat:savanna|feature:a trunk and big ears
giraffe|ungulate|sound:humms|diet:acacia leaves|habitat:african savanna|feature:the tallest animal
zebra|equine|sound:neighs|diet:grass|habitat:african plains|feature:black and white stripes
monkey|primate|sound:chatters|diet:fruit and insects|habitat:forests|feature:a long balancing tail
gorilla|primate|sound:grunts|diet:leaves and stems|habitat:african mountains|feature:the largest primate
chimpanzee|primate|sound:hoots|diet:fruit and termites|habitat:african forests|feature:uses tools
kangaroo|marsupial|sound:hops silently|diet:grass|habitat:australia|feature:carries its joey in a pouch
koala|marsupial|sound:snores softly|diet:eucalyptus leaves|habitat:australian forests|feature:sleeps most of the day
panda|ursid|sound:bleats|diet:bamboo|habitat:chinese mountains|feature:black and white bear
camel|ungulate|sound:grunts|diet:dry plants|habitat:deserts|feature:a hump that stores fat
donkey|equine|sound:heehaws|diet:grass and hay|role:carries loads|feature:long ears
mouse|rodent|sound:squeaks|diet:seeds and crumbs|habitat:everywhere people live|feature:fast and tiny
rat|rodent|sound:squeaks|diet:almost anything|habitat:cities and fields|feature:a long scaly tail
squirrel|rodent|sound:chatters|diet:nuts and acorns|habitat:forests|feature:buries nuts for winter
rabbit|lagomorph|sound:thumps|diet:grass and carrots|habitat:meadows|feature:long ears and big hops
deer|cervid|sound:bells|diet:leaves and grass|habitat:forests|feature:grows antlers each year
moose|cervid|sound:bellowing call|diet:water plants and twigs|habitat:northern forests|feature:huge flat antlers
raccoon|procyonid|sound:chittering|diet:almost anything|habitat:woods and cities|feature:masked face, clever hands
skunk|mephitid|sound:hisses|diet:insects and eggs|habitat:woodlands|feature:sprays a terrible smell
bat|mammal|sound:high screeches|diet:insects and fruit|habitat:caves|feature:the only flying mammal
whale|cetacean|sound:sings|diet:krill and fish|habitat:oceans|feature:the biggest animal alive
dolphin|cetacean|sound:clicks and whistles|diet:fish|habitat:warm seas|feature:smart, plays in waves
seal|pinniped|sound:barks|diet:fish|habitat:coasts|feature:swims fast, waddles on land
walrus|pinniped|sound:grunts|diet:clams|habitat:arctic coasts|feature:long ivory tusks
manatee|sirenian|sound:soft chirps|diet:sea grass|habitat:warm rivers|feature:a gentle sea cow
hedgehog|erinaceid|sound:snuffles|diet:insects|habitat:hedges|feature:rolls into a spike ball
otter|mustelid|sound:chirps|diet:fish and shellfish|habitat:rivers|feature:plays on its back in water
beaver|rodent|sound:tail slaps|diet:bark|habitat:rivers|feature:builds dams
badger|mustelid|sound:growls|diet:worms and grubs|habitat:underground setts|feature:striped face
sloth|pilosa|sound:soft hiss|diet:leaves|habitat:rainforest canopy|feature:moves in slow motion
armadillo|cingulata|sound:grunts|diet:insects|habitat:grasslands|feature:armor shell
anteater|pilosa|sound:snorts|diet:ants and termites|habitat:grasslands|feature:a two-foot sticky tongue
hamster|rodent|sound:quiet squeaks|diet:seeds and grains|role:a small pet|feature:stuffs cheeks with food
ferret|mustelid|sound:dooks|diet:meat|role:a playful pet|feature:long flexible body
weasel|mustelid|sound:shrill chatter|diet:rodents|habitat:fields|feature:slippery and quick
wolverine|mustelid|sound:growls|diet:whatever it can catch|habitat:northern wilds|feature:fearless and strong
lynx|felid|sound:yowls|diet:hares|habitat:northern forests|feature:tufted ears and a stub tail
bobcat|felid|sound:yowls|diet:rabbits and birds|habitat:north america|feature:a bobbed tail
cougar|felid|sound:whistles|diet:deer|habitat:mountains|feature:also called puma or mountain lion
jaguar|felid|sound:deep growls|diet:capybara and fish|habitat:rainforests|feature:rosette spots, strong jaws
leopard|felid|sound:sawing rasps|diet:antelope|habitat:africa and asia|feature:spots, drags prey up trees
cheetah|felid|sound:chirps|diet:gazelles|habitat:african plains|feature:the fastest land animal
hyena|hyaenid|sound:whooping laughs|diet:leftovers and prey|habitat:african plains|feature:powerful jaws
meerkat|mongoose|sound:peeping calls|diet:insects|habitat:deserts|feature:stands guard upright
mongoose|carnivoran|sound:chitters|diet:snakes and rodents|habitat:asia and africa|feature:famously fights cobras
porcupine|rodent|sound:quill rattles|diet:bark and plants|habitat:forests|feature:coat of quills
chinchilla|rodent|sound:soft squeaks|diet:grass and seeds|habitat:andes mountains|feature:the softest fur
guinea pig|rodent|sound:wheeks|diet:grass and veggies|role:a gentle pet|feature:never stops eating
capybara|rodent|sound:clicks|diet:grass|habitat:south american rivers|feature:the biggest rodent
opossum|marsupial|sound:hisses|diet:almost anything|habitat:americas|feature:plays dead when scared
wombat|marsupial|sound:grunts|diet:grass roots|habitat:australia|feature:cubes for droppings
wallaby|marsupial|sound:thumps|diet:grass|habitat:australia|feature:a small kangaroo
lemur|primate|sound:singing calls|diet:fruit|habitat:madagascar|feature:big round eyes
baboon|primate|sound:barks|diet:fruit and grubs|habitat:african cliffs|feature:a dog-like muzzle
orangutan|primate|sound:long calls|diet:fruit|habitat:borneo rainforests|feature:builds a new nest each night
gibbon|primate|sound:singing duets|diet:fruit|habitat:asian treetops|feature:swings branch to branch
aardvark|tubulidentata|sound:snorts|diet:ants and termites|habitat:african night|feature:digs like a machine
pangolin|pholidota|sound:hisses|diet:ants|habitat:africa and asia|feature:scale armor, rolls up
rhinoceros|ungulate|sound:snorts|diet:grass|habitat:savanna|feature:a horn on the nose
hippopotamus|ungulate|sound:grunts and bellows|diet:grass|habitat:african rivers|feature:opens its mouth four feet wide
bison|bovine|sound:grunts|diet:grass|habitat:great plains|feature:the biggest land animal in america
buffalo|bovine|sound:low bellows|diet:grass|habitat:africa and asia|feature:curved horns
yak|bovine|sound:grunts|diet:grass|habitat:himalayas|feature:a shaggy coat for the cold
llama|ungulate|sound:humming|diet:grass|role:carries loads|feature:spits when annoyed
alpaca|ungulate|sound:humming|diet:grass|role:gives soft wool|feature:a fluffy face
narwhal|cetacean|sound:clicks|diet:fish|habitat:arctic seas|feature:a spiral tusk
orca|cetacean|sound:pods of calls|diet:seals and fish|habitat:all oceans|feature:actually the biggest dolphin
porpoise|cetacean|sound:soft clicks|diet:fish|habitat:cool northern seas|feature:a blunt-nosed small whale
dugong|sirenian|sound:chirps|diet:sea grass|habitat:warm coasts|feature:the manatee's sea cousin
sea lion|pinniped|sound:loud barks|diet:fish|habitat:rocky coasts|feature:can walk on its flippers
mole|talpid|sound:faint squeaks|diet:earthworms|habitat:underground|feature:digs tunnels with spade hands
shrew|soricid|sound:high twitter|diet:insects|habitat:leaf litter|feature:a tiny fast heartbeat
chipmunk|rodent|sound:chip-chip calls|diet:nuts and seeds|habitat:woods|feature:striped back, cheek pouches
groundhog|rodent|sound:whistles|diet:plants|habitat:meadows|feature:predicts spring in stories
gerbil|rodent|sound:faint thumps|diet:seeds|role:a small pet|feature:long fuzzy tail
lemming|rodent|sound:squeaks|diet:grass and moss|habitat:arctic tundra|feature:population booms
prairie dog|rodent|sound:barking calls|diet:grass|habitat:prairie towns|feature:digs whole underground villages
wildebeest|antelope|sound:grunts and snorts|diet:grass|habitat:african plains|feature:migrates in herds
antelope|bovine|sound:snorts|diet:grass|habitat:savanna|feature:graceful curved horns
gazelle|antelope|sound:faint grunts|diet:grass and shoots|habitat:africa|feature:leaps to show off
impala|antelope|sound:snorts|diet:grass|habitat:savanna|feature:jumps nine meters
elk|cervid|sound:bugling|diet:grass and bark|habitat:mountain forests|feature:the largest deer
caribou|cervid|sound:clicking tendons|diet:lichen|habitat:arctic tundra|feature:both sexes grow antlers
reindeer|cervid|sound:grunts|diet:lichen|habitat:arctic|role:pulls sleighs in stories|feature:a thick winter coat
eagle|raptor|sound:high cries|diet:fish and small mammals|habitat:cliffs and tall trees|feature:hooks its prey with talons
hawk|raptor|sound:sharp kee-kee|diet:rodents|habitat:open country|feature:superb eyesight
falcon|raptor|sound:kak-kak|diet:birds in mid-air|habitat:everywhere|feature:the fastest animal in a dive
owl|bird|sound:hoots|diet:mice|habitat:night woods|feature:turns its head almost all the way around
parrot|bird|sound:mimics words|diet:seeds and fruit|habitat:tropics|feature:can learn to talk
parakeet|parrot|sound:cheerful chattering|diet:seeds|role:a small pet|feature:a long tail on a small body
macaw|parrot|sound:loud squawks|diet:nuts and fruit|habitat:rainforests|feature:a meter of rainbow feathers
cockatoo|parrot|sound:creaky calls|diet:seeds|habitat:australia|feature:a crest it raises when excited
crow|corvid|sound:caw caw|diet:almost anything|habitat:everywhere|feature:one of the smartest birds
raven|corvid|sound:deep croaks|diet:almost anything|habitat:wild places|feature:solves puzzles for fun
sparrow|songbird|sound:chirp chirp|diet:seeds|habitat:cities and farms|feature:hops rather than walks
robin|songbird|sound:morning song|diet:worms|habitat:gardens|feature:a red-orange breast
cardinal|songbird|sound:loud whistles|diet:seeds|habitat:backyards|feature:the male is all red
finch|songbird|sound:trills|diet:seeds|habitat:everywhere|feature:beaks shaped by what they eat
canary|songbird|sound:beautiful song|diet:seeds|role:a singing pet|feature:small and yellow
pigeon|dove|sound:cooing|diet:grain and crumbs|habitat:city streets|feature:finds its way home across countries
dove|bird|sound:soft coos|diet:seeds|habitat:towns and woods|feature:the symbol of peace
seagull|gull|sound:laughing cries|diet:fish and chips|habitat:coasts|feature:steals food mid-air
albatross|seabird|sound:bill clacking|diet:squid|habitat:southern oceans|feature:the longest wingspan
penguin|seabird|sound:braying calls|diet:fish|habitat:antarctica|feature:swims instead of flying
ostrich|rhea|sound:booming hums|diet:plants and lizards|habitat:african savanna|feature:the biggest bird, runs 70 km/h
emu|rhea|sound:drumming booms|diet:seeds and insects|habitat:australia|feature:the second-biggest bird
kiwi|bird|sound:shrill whistles|diet:insects|habitat:new zealand|feature:eggs half its body weight
flamingo|bird|sound:goose-like honks|diet:tiny shrimp|habitat:salt lakes|feature:pink from what it eats
pelican|seabird|sound:grunting|diet:fish|habitat:coasts|feature:a beak pouch that holds gallons
duck|fowl|sound:quacks|diet:plants and insects|habitat:ponds|feature:water rolls off its back
goose|duck|sound:honks|diet:grass|habitat:lakes|feature:flies in a v formation
swan|duck|sound:trumpeting|diet:water plants|habitat:lakes|feature:mates for life
chicken|fowl|sound:clucks|diet:grain|role:eggs and meat|feature:dust-bathes to clean up
rooster|fowl|sound:cock-a-doodle-doo|diet:grain|role:wakes the farm|feature:crows at first light
turkey|fowl|sound:gobbles|diet:seeds and acorns|habitat:american woods|feature:the male fans its tail
peacock|fowl|sound:loud cries|diet:seeds|habitat:india|feature:the male fans a jewel tail
woodpecker|bird|sound:drumming on trees|diet:beetles|habitat:forests|feature:hammer-pecks 20 times a second
hummingbird|bird|sound:wing buzz|diet:nectar|habitat:americas|feature:hovers backwards
kingfisher|bird|sound:sharp whistles|diet:small fish|habitat:riverbanks|feature:dives like a dart
toucan|bird|sound:croaking|diet:fruit|habitat:rainforests|feature:a beak half its body
vulture|bird|sound:hisses|diet:leftovers|habitat:open country|feature:cleans up what falls
crane|bird|sound:bugling calls|diet:grain and frogs|habitat:wetlands|feature:dances to bond
stork|bird|sound:bill clattering|diet:fish|habitat:wetlands|feature:delivers babies in stories
heron|bird|sound:harsh croaks|diet:fish|habitat:shallow water|feature:stands still as a statue
puffin|auk|sound:low growls|diet:fish|habitat:sea cliffs|feature:a rainbow-striped beak
magpie|corvid|sound:chattering|diet:almost anything|habitat:gardens|feature:collects shiny things
starling|songbird|sound:whistles and mimicry|diet:insects|habitat:cities|feature:clouds of thousands in flight
swallow|songbird|sound:twittering|diet:flying insects|habitat:barns|feature:migrates the whole globe
salmon|salmonid|sound:n/a|diet:smaller fish|habitat:rivers then ocean|feature:swims home up waterfalls
tuna|fish_cat|sound:n/a|diet:squid and fish|habitat:open ocean|feature:swims nonstop, warm-blooded
trout|salmonid|sound:n/a|diet:insects|habitat:cold streams|feature:spotted sides
cod|fish_cat|sound:n/a|diet:small fish|habitat:cold seas|feature:the classic fish and chips
shark|fish_cat|sound:n/a|diet:fish and seals|habitat:all oceans|feature:grows new teeth forever
ray|rayskate|sound:n/a|diet:shellfish|habitat:sea floors|feature:flies underwater like a kite
eel|fish_cat|sound:n/a|diet:small animals|habitat:rivers and seas|feature:snake-long and slippery
seahorse|pipefish|sound:n/a|diet:tiny crustaceans|habitat:sea grass|feature:the male carries the babies
clownfish|damselfish|sound:pops|diet:plankton|habitat:sea anemones|feature:lives un-stung among tentacles
goldfish|carp|sound:n/a|diet:flakes|role:a first pet|feature:remembers for months
pufferfish|puffer|sound:n/a|diet:shellfish|habitat:warm seas|feature:puffs into a spiky ball
swordfish|billfish|sound:n/a|diet:squid|habitat:open ocean|feature:a sword for a nose
piranha|fish_cat|sound:drumming|diet:fish and seeds|habitat:amazon rivers|feature:razor teeth in schools
catfish|fish_cat|sound:n/a|diet:whatever sinks|habitat:rivers|feature:whiskers that taste the water
sardine|clupeid|sound:n/a|diet:plankton|habitat:schools in the sea|feature:millions swim as one
anchovy|clupeid|sound:n/a|diet:plankton|habitat:sea schools|feature:tiny and salty
mackerel|fish_cat|sound:n/a|diet:small fish|habitat:open sea|feature:striped and fast
snake|reptile|sound:hisses|diet:rodents and eggs|habitat:everywhere warm|feature:smells with its tongue
cobra|elapid|sound:growling hiss|diet:rodents|habitat:asia and africa|feature:spreads a hood, spits venom
python|snake|sound:hisses|diet:birds and mammals|habitat:tropics|feature:squeezes its prey
rattlesnake|viper|sound:a shaking rattle|diet:rodents|habitat:americas|feature:warns before it bites
boa|snake|sound:hisses|diet:rodents|habitat:americas|feature:constricts like pythons
anaconda|boa|sound:hisses|diet:capybara|habitat:amazon swamps|feature:the heaviest snake
lizard|reptile|sound:n/a|diet:insects|habitat:rocks and walls|feature:regrows its tail
gecko|lizard|sound:chirps|diet:insects|habitat:walls and ceilings|feature:feet that stick to glass
iguana|lizard|sound:head-bobbing|diet:leaves|habitat:tropics|feature:a spine sail down its back
chameleon|lizard|sound:faint hisses|diet:insects|habitat:africa|feature:changes color, eyes move apart
komodo dragon|monitor|sound:hisses|diet:pigs and deer|habitat:indonesian islands|feature:the biggest lizard
turtle|reptile|sound:n/a|diet:plants and fish|habitat:sea and ponds|feature:carries its house
tortoise|turtle|sound:n/a|diet:grass|habitat:dry land|feature:lives over a hundred years
crocodile|croc|sound:bellowing roars|diet:zebra and fish|habitat:rivers|feature:the strongest bite ever measured
alligator|croc|sound:bellowing|diet:fish and turtles|habitat:swamps|feature:u-shaped snout
frog|amphibian|sound:croaks|diet:insects|habitat:ponds|feature:breathes through its skin
toad|frog|sound:warty croaks|diet:insects|habitat:gardens|feature:dry bumpy skin
salamander|amphibian|sound:n/a|diet:insects|habitat:damp woods|feature:regrows whole legs
newt|salamander|sound:n/a|diet:small water animals|habitat:ponds|feature:a bright warning belly
axolotl|salamander|sound:n/a|diet:worms|habitat:mexican lakes|feature:stays a larva forever, regrows anything
ant|insect|sound:n/a|diet:almost anything|habitat:colonies everywhere|feature:carries 50 times its weight
bee|insect|sound:buzzing|diet:nectar|habitat:hives|feature:makes honey, dances directions
wasp|insect|sound:buzzing|diet:insects and sugar|habitat:nests|feature:paper nests, painful sting
hornet|wasp|sound:deep buzz|diet:other insects|habitat:trees|feature:the biggest wasp
butterfly|lepidoptera|sound:n/a|diet:nectar|habitat:gardens|feature:caterpillar turns into wings
moth|lepidoptera|sound:n/a|diet:wool and nectar|habitat:night|feature:flies to lamps
beetle|insect|sound:n/a|diet:plants|habitat:everywhere|feature:the most species of any animal
ladybug|beetle|sound:n/a|diet:aphids|habitat:gardens|feature:eats garden pests
firefly|beetle|sound:n/a|diet:pollen|habitat:summer nights|feature:glows to talk
dragonfly|insect|sound:n/a|diet:mosquitoes|habitat:ponds|feature:four wings, flies any direction
grasshopper|insect|sound:stridulation|diet:grass|habitat:meadows|feature:jumps 20 times its length
cricket|insect|sound:chirping legs|diet:plants|habitat:grass|feature:sings by rubbing wings
mantis|mantid|sound:n/a|diet:other insects|habitat:plants|feature:prayer arms, hunts head-on
cockroach|roach|sound:n/a|diet:everything|habitat:warm buildings|feature:outlives almost anything
termite|insect|sound:head-banging|diet:wood|habitat:mounds|feature:builds air-conditioned towers
flea|insect|sound:n/a|diet:blood|habitat:pet fur|feature:jumps 200 times its size
mosquito|insect|sound:a thin whine|diet:nectar and blood|habitat:standing water|feature:the deadliest animal to humans
spider|arachnid|sound:n/a|diet:insects|habitat:webs and holes|feature:spins silk stronger than steel
tarantula|spider|sound:n/a|diet:insects|habitat:burrows|feature:foot-long leg span
scorpion|arachnid|sound:n/a|diet:insects|habitat:deserts|feature:glows under uv light
crab|crustacean|sound:n/a|diet:whatever it finds|habitat:beaches|feature:walks sideways
lobster|crustacean|sound:n/a|diet:shellfish|habitat:atlantic floor|feature:claws that crush and cut
shrimp|crustacean|sound:n/a|diet:plankton|habitat:seas|feature:snaps a bubble louder than a gun
crayfish|crab|sound:n/a|diet:plants|habitat:freshwater|feature:mini freshwater lobster
snail|mollusk|sound:n/a|diet:leaves|habitat:gardens|feature:carries a spiral house
slug|snail|sound:n/a|diet:plants|habitat:damp shade|feature:a houseless snail
clam|bivalve|sound:n/a|diet:plankton|habitat:buried in sand|feature:siphons the water for food
oyster|bivalve|sound:n/a|diet:plankton|habitat:sea beds|feature:coats grit into pearls
octopus|octopod|sound:n/a|diet:crabs|habitat:rocky sea floor|feature:three hearts, changes color
squid|mollusk|sound:n/a|diet:fish|habitat:deep sea|feature:eight arms, two tentacles
jellyfish|invertebrate|sound:n/a|diet:plankton|habitat:all oceans|feature:stings without a brain
starfish|invertebrate|sound:n/a|diet:shellfish|habitat:sea floors|feature:grows back lost arms
coral|invertebrate|sound:n/a|diet:plankton|habitat:reefs|feature:an animal that builds cities
earthworm|worm|sound:n/a|diet:soil|habitat:dirt|feature:farms the ground for us
oak|tree_cat|part:acorns|feature:the strongest common wood
pine|tree_cat|part:pine cones|feature:evergreen needles
maple|tree_cat|part:helicopter seeds|feature:sap that becomes syrup
birch|tree_cat|feature:white peeling bark
willow|tree_cat|feature:drooping branches over water
cedar|tree_cat|feature:scented red wood
palm|tree_cat|part:coconuts|feature:fronds that survive storms
baobab|tree_cat|feature:a trunk like a water tower
sequoia|tree_cat|feature:the biggest living thing on earth
bamboo|grass_cat|feature:grows a meter in a day
rose|flower_cat|feature:thorns and perfume
tulip|flower_cat|feature:a cup that closes at night
sunflower|flower_cat|feature:turns to face the sun
daisy|flower_cat|feature:opens at dawn
lily|flower_cat|feature:a perfume that fills a room
orchid|flower_cat|feature:tricks insects into pollinating
lotus|flower_cat|feature:rises clean from muddy water
daffodil|flower_cat|feature:the first flower of spring
lavender|flower_cat|feature:a scent that calms
hibiscus|flower_cat|feature:blooms one day only
cactus|desert plant|feature:stores years of water inside
fern|plant|feature:older than the dinosaurs
moss|plant|feature:a forest's soft carpet
ivy|plant|feature:climbs whole walls
wheat|grass_cat|role:makes flour|feature:the crop that feeds the world
rice|grass_cat|role:feeds half of humanity|feature:grows in paddies
corn|grass_cat|part:kernels|feature:grows waist-high in a summer
dragon|mythical_cat|status:mythical|feature:breathes fire in every legend
unicorn|mythical_cat|status:mythical|feature:a horn only the pure can touch
mermaid|mythical_cat|status:mythical|feature:half woman, half fish
phoenix|mythical_cat|status:mythical|feature:burns to ash and is reborn
fairy|mythical_cat|status:mythical|feature:tiny wings and magic dust
elf|mythical_cat|status:mythical|feature:immortal and mischievous in tales
giant|mythical_cat|status:mythical|feature:big enough to step over rivers
troll|mythical_cat|status:mythical|feature:turns to stone in sunlight
goblin|mythical_cat|status:mythical|feature:sneaky and gold-hungry
werewolf|mythical_cat|status:mythical|feature:a person that turns with the full moon
vampire|mythical_cat|status:mythical|feature:drinks blood, fears garlic
ghost|mythical_cat|status:mythical|feature:a soul that lingers
zombie|mythical_cat|status:mythical|feature:walks dead, wants brains in films
kraken|mythical_cat|status:mythical|feature:a sea monster the size of an island
yeti|mythical_cat|status:mythical|feature:an abominable snowman
bigfoot|mythical_cat|status:mythical|feature:footprints but never a sighting
centaur|mythical_cat|status:mythical|feature:half man, half horse
pegasus|mythical_cat|status:mythical|feature:a winged white horse
griffin|mythical_cat|status:mythical|feature:lion body, eagle head
leprechaun|mythical_cat|status:mythical|feature:hides gold at the rainbow's end
hydra|mythical_cat|status:mythical|feature:two heads grow back for one
sphinx|mythical_cat|status:mythical|feature:asks riddles at the crossroads
"""

# intermediate family links so chains have real depth
FAMILY_LINKS = [
    ("proboscidean", "ungulate"), ("lagomorph", "mammal"), ("cervid", "ungulate"),
    ("procyonid", "carnivoran"), ("mephitid", "carnivoran"), ("mustelid", "carnivoran"),
    ("carnivoran", "mammal"), ("hyaenid", "carnivoran"), ("mongoose", "carnivoran"),
    ("erinaceid", "insectivore"), ("talpid", "insectivore"), ("soricid", "insectivore"),
    ("insectivore", "mammal"), ("bat", "mammal"), ("pilosa", "mammal"),
    ("cingulata", "mammal"), ("sirenian", "cetacean"), ("pinniped", "carnivoran"),
    ("raptor", "bird"), ("owl", "bird"), ("parrot", "bird"), ("corvid", "songbird"),
    ("songbird", "bird"), ("dove", "bird"), ("gull", "seabird"), ("seabird", "bird"),
    ("penguin", "seabird"), ("rhea", "bird"), ("emu", "rhea"), ("kiwi", "bird"),
    ("flamingo", "bird"), ("pelican", "seabird"), ("duck", "fowl"), ("fowl", "bird"),
    ("auk", "seabird"), ("salmonid", "fish_cat"), ("tuna", "fish_cat"),
    ("cod", "fish_cat"), ("shark", "fish_cat"), ("rayskate", "fish_cat"),
    ("eel", "fish_cat"), ("pipefish", "fish_cat"), ("damselfish", "fish_cat"),
    ("carp", "fish_cat"), ("puffer", "fish_cat"), ("billfish", "fish_cat"),
    ("piranha", "fish_cat"), ("catfish", "fish_cat"), ("clupeid", "fish_cat"),
    ("mackerel", "fish_cat"), ("elapid", "snake"), ("python", "snake"),
    ("viper", "snake"), ("boa", "snake"), ("snake", "reptile"),
    ("gecko", "lizard"), ("iguana", "lizard"), ("chameleon", "lizard"),
    ("monitor", "lizard"), ("lizard", "reptile"), ("turtle", "reptile"),
    ("croc", "reptile"), ("frog", "amphibian"), ("salamander", "amphibian"),
    ("ant", "insect"), ("bee", "insect"), ("wasp", "insect"),
    ("lepidoptera", "insect"), ("beetle", "insect"), ("dragonfly", "insect"),
    ("grasshopper", "insect"), ("cricket", "insect"), ("mantid", "insect"),
    ("roach", "insect"), ("termite", "insect"), ("flea", "insect"),
    ("mosquito", "insect"), ("spider", "arachnid"), ("scorpion", "arachnid"),
    ("crab", "crustacean"), ("lobster", "crustacean"), ("shrimp", "crustacean"),
    ("snail", "mollusk"), ("bivalve", "mollusk"), ("octopod", "mollusk"),
    ("squid", "mollusk"), ("jellyfish", "invertebrate"), ("starfish", "invertebrate"),
    ("coral", "invertebrate"), ("worm", "invertebrate"),
    ("desert plant", "plant"), ("grass_cat", "plant"),
]

# intermediate living-world category links (parent pairs, no defs needed)
LIVING_LINKS = [
    ("proboscidean", "ungulate"), ("lagomorph", "mammal"), ("cervid", "ungulate"),
    ("procyonid", "carnivoran"), ("mephitid", "carnivoran"), ("mustelid", "carnivoran"),
    ("carnivoran", "mammal"), ("hyaenid", "carnivoran"), ("mongoose", "carnivoran"),
    ("erinaceid", "insectivore"), ("talpid", "insectivore"), ("soricid", "insectivore"),
    ("insectivore", "mammal"), ("pilosa", "mammal"), ("cingulata", "mammal"),
    ("sirenian", "cetacean"), ("pinniped", "carnivoran"), ("raptor", "bird"),
    ("owl", "bird"), ("parrot", "bird"), ("corvid", "songbird"), ("songbird", "bird"),
    ("dove", "bird"), ("gull", "seabird"), ("seabird", "bird"), ("penguin", "seabird"),
    ("rhea", "bird"), ("emu", "rhea"), ("kiwi", "bird"), ("flamingo", "bird"),
    ("pelican", "seabird"), ("duck", "fowl"), ("fowl", "bird"), ("auk", "seabird"),
    ("salmonid", "fish_cat"), ("tuna", "fish_cat"), ("cod", "fish_cat"),
    ("shark", "fish_cat"), ("rayskate", "fish_cat"), ("eel", "fish_cat"),
    ("pipefish", "fish_cat"), ("damselfish", "fish_cat"), ("carp", "fish_cat"),
    ("puffer", "fish_cat"), ("billfish", "fish_cat"), ("piranha", "fish_cat"),
    ("catfish", "fish_cat"), ("clupeid", "fish_cat"), ("mackerel", "fish_cat"),
    ("elapid", "snake"), ("python", "snake"), ("viper", "snake"), ("boa", "snake"),
    ("snake", "reptile"), ("gecko", "lizard"), ("iguana", "lizard"),
    ("chameleon", "lizard"), ("monitor", "lizard"), ("lizard", "reptile"),
    ("turtle", "reptile"), ("croc", "reptile"), ("frog", "amphibian"),
    ("salamander", "amphibian"), ("ant", "insect"), ("bee", "insect"),
    ("wasp", "insect"), ("lepidoptera", "insect"), ("beetle", "insect"),
    ("dragonfly", "insect"), ("grasshopper", "insect"), ("cricket", "insect"),
    ("mantid", "insect"), ("roach", "insect"), ("termite", "insect"),
    ("flea", "insect"), ("mosquito", "insect"), ("spider", "arachnid"),
    ("scorpion", "arachnid"), ("crab", "crustacean"), ("lobster", "crustacean"),
    ("shrimp", "crustacean"), ("snail", "mollusk"), ("bivalve", "mollusk"),
    ("octopod", "mollusk"), ("squid", "mollusk"), ("jellyfish", "invertebrate"),
    ("starfish", "invertebrate"), ("coral", "invertebrate"), ("worm", "invertebrate"),
]

# ============================ TAXONOMY 2 — the made world ======================
MADE_SPINE = [
    cat("artifact", ["artifact", "man-made thing"], "a thing made by people", "entity"),
    cat("tool", ["tool"], "a hand-held thing that does a job", "artifact"),
    cat("machine", ["machine"], "a thing with moving parts that does work", "artifact"),
    cat("device", ["device", "gadget"], "a machine made for one purpose, often electronic", "machine"),
    cat("vehicle", ["vehicle"], "a machine that carries people or things", "machine"),
    cat("furniture", ["furniture"], "movable things that make a room usable", "artifact"),
    cat("clothing", ["clothing", "clothes", "garment"], "things people wear", "artifact"),
    cat("container", ["container", "vessel"], "a thing that holds something inside", "artifact"),
    cat("instrument", ["instrument", "musical instrument"], "a thing built to make music", "artifact"),
    cat("weapon", ["weapon"], "a thing made to fight or hunt with", "artifact"),
    cat("toy", ["toy"], "a thing made for play", "artifact"),
    cat("structure", ["structure"], "a big thing people build", "artifact"),
    cat("building", ["building"], "a structure with walls and a roof that people use", "structure"),
    cat("place_cat", ["place", "location"], "a spot or area where things are", "entity"),
    cat("room_cat", ["room"], "an inside space of a building", "place_cat"),
    cat("landmark", ["landmark"], "a famous place people travel to see", "place_cat"),
    cat("landform", ["landform"], "a shape of the natural land or water", "place_cat"),
    cat("matter", ["matter", "substance"], "the physical stuff things are made of", "entity"),
    cat("material", ["material"], "matter used to make things", "matter"),
    cat("food_cat", ["food"], "stuff living things eat for energy", "matter"),
    cat("dish", ["dish", "meal"], "a food made by combining and cooking", "food_cat"),
    cat("drink", ["drink", "beverage"], "a liquid for drinking", "food_cat"),
    cat("person_cat", ["person", "human"], "a human being", "organism"),
    cat("role_cat", ["role", "job", "occupation"], "the work a person does", "idea"),
    cat("body_part", ["body part"], "a part of a living body", "entity"),
    cat("time_cat", ["time", "unit of time"], "a measure of when and how long", "idea"),
    cat("game_cat", ["game"], "a structured way of playing with rules", "idea"),
    cat("sport", ["sport"], "a physical game of skill and effort", "game_cat"),
    cat("color_cat", ["color"], "the look of light on a thing", "idea"),
    cat("shape_cat", ["shape", "figure"], "the outer form of a thing", "idea"),
    cat("book_cat", ["book", "publication"], "bound pages with writing or pictures", "artifact"),
]

MADE = """
hammer|tool|used_for:driving nails|made_of:steel and wood
screwdriver|tool|used_for:turning screws|part:a flat or crossed tip
wrench|tool|used_for:gripping and turning bolts
saw|tool|used_for:cutting wood|part:toothed blade
drill|tool|used_for:boring holes|trait:spins fast
axe|tool|used_for:splitting wood|part:a heavy blade
chisel|tool|used_for:carving edges into wood or stone
shovel|tool|used_for:digging and moving soil|part:a broad blade
rake|tool|used_for:gathering leaves|part:a row of tines
scissors|tool|used_for:cutting paper and cloth|part:two blades and handles
knife|tool|used_for:cutting food|part:a sharp edge
fork|tool|used_for:lifting food to the mouth|part:pointed tines
spoon|tool|used_for:scooping food and soup|part:a small bowl
needle|tool|used_for:sewing cloth|part:an eye for thread
pin|tool|used_for:holding cloth together
brush|tool|used_for:painting or cleaning|part:bristles
broom|tool|used_for:sweeping floors|part:a bundle of straw
mop|tool|used_for:washing floors|part:a head of absorbent strands
bucket|container|used_for:carrying water|made_of:plastic or metal
ladder|tool|used_for:climbing to high places|part:two rails and rungs
tape_measure|tool|used_for:measuring length|trait:rolls back with a snap
level|tool|used_for:checking if a surface is flat
flashlight|device|used_for:making light in the dark|made_of:metal and a bulb
candle|tool|used_for:light and scent|made_of:wax and a wick
matches|tool|used_for:making fire|feature:a striking head
lighter|tool|used_for:making a flame anywhere
sewing_machine|machine|used_for:stitching cloth fast
wheelbarrow|tool|used_for:hauling loads on one wheel
scales|tool|used_for:measuring weight
thermometer|device|used_for:measuring temperature
compass|tool|used_for:finding north|feature:a needle that points north
magnifier|tool|used_for:making small things look big
rope|material|used_for:tying and pulling|made_of:twisted fibers
chain|tool|used_for:locking and lifting|made_of:linked metal rings
padlock|tool|used_for:locking doors and boxes
garden_hose|tool|used_for:watering plants|shape:a long flexible tube
watering_can|container|used_for:watering plants gently|part:a spout
sprinkler|device|used_for:watering lawns on its own
nets|tool|used_for:catching fish|made_of:knotted mesh
trap|tool|used_for:catching animals
glue|material|used_for:sticking things together|trait:sticky when wet
sandpaper|tool|used_for:smoothing wood|made_of:grit on paper
engine|machine|used_for:turning fuel into motion|trait:the heart of a vehicle
motor|machine|used_for:turning power into spin
pump|machine|used_for:pushing water or air
turbine|machine|used_for:making power from flow
generator|machine|used_for:making electricity
tractor|vehicle|used_for:farm work|trait:big wheels, slow and strong
bulldozer|vehicle|used_for:pushing earth|part:a wide front blade
crane|machine|used_for:lifting heavy loads high
forklift|vehicle|used_for:lifting pallets in warehouses
elevator|machine|used_for:moving people between floors|feature:a room that climbs cables
escalator|machine|used_for:carrying people up stairs without walking
washing_machine|machine|used_for:cleaning clothes with water and spin
dryer|machine|used_for:drying clothes with warm air
dishwasher|machine|used_for:washing dishes with spray
stove|machine|used_for:cooking with heat|part:burners and an oven
oven|machine|used_for:baking with steady heat
microwave|device|used_for:heating food fast with waves
refrigerator|device|used_for:keeping food cold and fresh|feature:runs day and night
freezer|device|used_for:keeping food frozen
toaster|device|used_for:browning bread|feature:springs the toast up
blender|device|used_for:liquifying food with spinning blades
mixer|device|used_for:beating dough and cream
coffee_maker|device|used_for:brewing coffee|part:a carafe
kettle|container|used_for:boiling water
air_conditioner|device|used_for:cooling a room|trait:humms by the window
fan|device|used_for:moving air|part:spinning blades
heater|device|used_for:warming a room
vacuum|machine|used_for:sucking dust off floors|trait:roars softly
printer|device|used_for:putting ink on paper from a computer
computer|device|used_for:thinking with electricity at your desk|part:screen and keyboard
laptop|device|used_for:computing on your lap
phone|device|used_for:talking across distances|feature:fits in a pocket
smartphone|device|used_for:calls, pictures and the internet in a pocket
television|device|used_for:showing moving pictures with sound
radio|device|used_for:hearing sound sent through air
camera|device|used_for:catching light as pictures
clock|device|used_for:showing the time|feature:hands or digits that move all day
watch|device|used_for:telling time on a wrist
calculator|device|used_for:doing arithmetic fast
scale_device|device|used_for:reading weight in numbers
battery|device|used_for:storing electricity|part:two terminals
charger|device|used_for:refilling a battery
plug|device|used_for:connecting a cord to power
wire|material|used_for:carrying electricity|made_of:copper
lightbulb|device|used_for:making light from electricity|shape:a glass bulb
lamp|device|used_for:lighting a corner of a room
doorbell|device|used_for:announcing a visitor|feature:a chime inside
smoke_alarm|device|used_for:screaming when smoke appears
thermostat|device|used_for:holding a steady temperature
solar_panel|device|used_for:making power from sunlight
wind_turbine|machine|used_for:making power from wind|part:three long blades
car|vehicle|used_for:driving on roads|part:four wheels and an engine
truck|vehicle|used_for:hauling heavy loads
bus|vehicle|used_for:carrying many people on routes
taxi|vehicle|used_for:rides for pay|feature:a roof sign
train|vehicle|used_for:hauling many cars on rails
tram|vehicle|used_for:gliding on street rails
subway|vehicle|used_for:fast travel under a city
bicycle|vehicle|used_for:riding on two wheels|trait:human powered
motorcycle|vehicle|used_for:fast riding on two wheels
scooter|vehicle|used_for:short rides standing up
skateboard|vehicle|used_for:rolling and tricks|part:a deck and four wheels
airplane|vehicle|used_for:flying through the sky|part:wings and jet engines
helicopter|vehicle|used_for:flying straight up|part:rotor blades on top
jet|vehicle|used_for:flying faster than sound can chase
rocket|vehicle|used_for:leaving the earth|feature:rides its own fire
boat|vehicle|used_for:crossing water|part:a hull
ship|vehicle|used_for:long voyages at sea|feature:big enough to carry trucks
submarine|vehicle|used_for:sailing under the sea
ferry|vehicle|used_for:carrying cars across water
canoe|vehicle|used_for:paddling quiet waters|made_of:light hull, paddled by hand
sailboat|vehicle|used_for:sailing on wind|part:a tall sail
sled|vehicle|used_for:sliding on snow
ambulance|vehicle|used_for:rushing the sick to help|feature:sirens and lights
firetruck|vehicle|used_for:fighting fires|part:ladders and hoses
police_car|vehicle|used_for:rushing to emergencies|feature:flashing lights
parachute|tool|used_for:falling slowly from the sky|shape:a canopy of cloth
wheel|part|used_for:rolling|shape:a circle that turns an axle
handlebar|part|used_for:steering a bike
seatbelt|part|used_for:holding you in a crash
tire|part|used_for:gripping the road|made_of:rubber
chair|furniture|used_for:sitting|part:four legs and a back
table|furniture|used_for:eating and working on|part:a flat top
desk|furniture|used_for:writing and computing
bed|furniture|used_for:sleeping|part:a mattress and frame
sofa|furniture|used_for:lounging together|trait:long and cushioned
couch|furniture|used_for:relaxing in a living room
bench|furniture|used_for:sitting outdoors or in parks
stool|furniture|used_for:sitting without a back|shape:leg and a round top
bookshelf|furniture|used_for:holding books|part:shelves
wardrobe|furniture|used_for:hanging clothes|part:doors and rails
dresser|furniture|used_for:folded clothes in drawers|part:drawers
nightstand|furniture|used_for:holding bedside things
crib|furniture|used_for:babies sleeping safe|part:high rails
rocking_chair|furniture|used_for:resting with a sway
hammock|furniture|used_for:sleeping between two trees|made_of:netting or cloth
mattress|furniture|used_for:soft sleep|made_of:springs and padding
pillow|furniture|used_for:resting your head|made_of:soft filling
blanket|furniture|used_for:warmth in bed|made_of:woven cloth
rug|furniture|used_for:warming a floor|made_of:woven fibers
curtain|furniture|used_for:darkening a window|made_of:hanging cloth
mirror|furniture|used_for:showing your reflection|made_of:coated glass
picture_frame|furniture|used_for:showing a photo on a wall
cabinet|furniture|used_for:storing kitchen things|part:doors and shelves
shelf|furniture|used_for:holding things on levels
coat_rack|furniture|used_for:hanging coats
lampshade|part|used_for:softening a lamp's light
shirt|clothing|used_for:dressing the top half|part:collar and sleeves
t-shirt|clothing|used_for:everyday comfort|trait:pulls over the head
pants|clothing|used_for:dressing the legs|part:two legs
jeans|clothing|used_for:hard-wearing pants|made_of:denim
shorts|clothing|used_for:keeping legs cool
skirt|clothing|used_for:a draped lower garment
dress|clothing|used_for:a one-piece outfit
coat|clothing|used_for:warmth in winter|trait:heavy and long
jacket|clothing|used_for:light outer wear
sweater|clothing|used_for:warmth by knitting|made_of:wool
hoodie|clothing|used_for:casual warmth|part:a hood
socks|clothing|used_for:cushioning feet in shoes
shoes|clothing|used_for:protecting feet for walking|part:soles
boots|clothing|used_for:hard ground and weather|trait:ankle-high
sandals|clothing|used_for:open-air walking
slippers|clothing|used_for:soft indoor steps
gloves|clothing|used_for:warm or safe hands
scarf|clothing|used_for:warmth around the neck
belt|clothing|used_for:holding pants up
hat|clothing|used_for:shading and warming the head
cap|clothing|used_for:sun shade with a brim|part:a visor
helmet|clothing|used_for:protecting the head
tie|clothing|used_for:dressing up formally
uniform|clothing|used_for:showing a job or team
pajamas|clothing|used_for:sleeping in comfort
swimsuit|clothing|used_for:swimming
raincoat|clothing|used_for:staying dry in rain|made_of:waterproof cloth
umbrella|tool|used_for:staying dry under rain|part:a folding canopy
apron|clothing|used_for:shielding clothes while cooking
vest|clothing|used_for:an extra warm layer
bottle|container|used_for:carrying drinks|made_of:glass or plastic
cup|container|used_for:hot drinks|part:a handle
mug|container|used_for:coffee and tea|trait:thick-walled
glass|container|used_for:cold drinks|made_of:clear glass
plate|container|used_for:serving food flat
bowl|container|used_for:serving food round
pot|container|used_for:cooking on heat|made_of:metal
pan|container|used_for:frying on heat|part:a long handle
jar|container|used_for:preserving food|part:a screw lid
can|container|used_for:sealed food and drink|made_of:thin metal
box|container|used_for:storing and shipping|shape:square corners
basket|container|used_for:carrying with a handle|made_of:woven strips
bag|container|used_for:carrying by hand or shoulder
backpack|container|used_for:carrying on the back|part:two straps
suitcase|container|used_for:traveling with clothes|part:a pull handle
barrel|container|used_for:storing big volumes|shape:a round bulge
crate|container|used_for:stacking goods|made_of:slats
trunk|container|used_for:old-fashioned travel storage
thermos|container|used_for:keeping drinks hot for hours
teapot|container|used_for:pouring tea|part:spout and lid
pitcher|container|used_for:pouring cold drinks
straw|tool|used_for:sipping drinks
guitar|instrument|used_for:strumming music|part:six strings and a sound hole
piano|instrument|used_for:pressing keys into music|feature:88 keys
violin|instrument|used_for:bowing music|part:four strings
drums|instrument|used_for:beating rhythm|part:a skin stretched over shell
flute|instrument|used_for:blowing melodies|shape:a slender tube
trumpet|instrument|used_for:brassy fanfares|part:three valves
saxophone|instrument|used_for:smooth jazz lines
harp|instrument|used_for:plucking long strings|shape:tall frame
banjo|instrument|used_for:twanging folk strings
cello|instrument|used_for:deep bowed notes|trait:played seated
harmonica|instrument|used_for:pocket-sized blues|trait:blown while held
organ|instrument|used_for:church-filling sound|part:pipes and keys
accordion|instrument|used_for:squeezing out melodies|part:folded bellows
xylophone|instrument|used_for:striking wooden notes
microphone|device|used_for:making a voice loud
speaker|device|used_for:turning current into sound
headphones|device|used_for:private listening
sword|weapon|used_for:old battles and duels|part:blade and hilt
shield|weapon|used_for:blocking blows|shape:a broad plate
bow_and_arrow|weapon|used_for:shooting arrows|part:a string and shaft
spear|weapon|used_for:thrusting at a distance|part:a point on a pole
cannon|weapon|used_for:heavy old firepower
rifle|weapon|used_for:accurate shooting
doll|toy|used_for:pretend play|shape:a small figure
teddy_bear|toy|used_for:cuddling|made_of:soft fur and stuffing
puzzle|toy|used_for:fitting pieces into a picture
blocks|toy|used_for:building towers
kite|toy|used_for:flying on wind|part:a tail and string
yo-yo|toy|used_for:spinning tricks on a string
top|toy|used_for:spinning on its point
marbles|toy|used_for:rolling games|made_of:glass balls
puppet|toy|used_for:acting with your hand
crayons|toy|used_for:coloring pictures|made_of:wax sticks
teddy|toy|used_for:comfort at night
robot_toy|toy|used_for:walking and blinking play
board_game|toy|used_for:family rivalries by rule|part:a board and pieces
deck_of_cards|toy|used_for:hundreds of games in 52 cards
dice|toy|used_for:adding chance to games|shape:cubes with dots
ball|toy|used_for:bouncing games|shape:a round sphere
frisbee|toy|used_for:gliding throws|shape:a flying disc
trampoline|toy|used_for:bouncing high|part:a sprung mat
skipping_rope|toy|used_for:rhythm jumping
castle|building|used_for:defending in the middle ages|part:towers and walls
house|building|used_for:living in|part:rooms under one roof
apartment|building|used_for:housing many families stacked up
skyscraper|building|used_for:office life in the clouds|feature:dozens of floors tall
office|building|used_for:working weekdays
school|building|used_for:learning with teachers
library|building|used_for:borrowing books quietly
hospital|building|used_for:healing the sick
church|building|used_for:worship|feature:a steeple and bells
temple|building|used_for:worship in old traditions
mosque|building|used_for:worship with a minaret
factory|building|used_for:making things on lines
warehouse|building|used_for:storing goods on pallets
station|building|used_for:catching trains
airport|building|used_for:boarding planes
stadium|building|used_for:watching games|feature:a ring of seats
theater|building|used_for:watching plays and films
museum|building|used_for:keeping history on display
hotel|building|used_for:paying to sleep away
restaurant|building|used_for:eating meals served to you
cafe|building|used_for:coffee and pastries
bank|building|used_for:keeping money safe
post_office|building|used_for:sending letters and parcels
farm|building|used_for:growing food and raising animals|part:fields and a barn
barn|building|used_for:sheltering animals and hay
greenhouse|building|used_for:growing plants under glass
lighthouse|building|used_for:warning ships with light|feature:stands at the shore
windmill|building|used_for:grinding grain with wind|part:sails that turn
bridge|structure|used_for:crossing rivers and gaps
tunnel|structure|used_for:passing through hills
dam|structure|used_for:holding rivers and making power
tower|structure|used_for:standing tall above a city
pyramid|structure|used_for:pharaohs resting in stone|shape:a square cone
fence|structure|used_for:marking borders
wall|structure|used_for:dividing and defending
well|structure|used_for:reaching groundwater
stairs|structure|used_for:climbing between floors|part:steps
chimney|structure|used_for:venting smoke|part:rises off the roof
gate|structure|used_for:opening in a fence
monument|structure|used_for:remembering people and events
kitchen|room_cat|used_for:cooking meals|part:stove, sink and counters
bedroom|room_cat|used_for:sleeping|part:a bed and a dresser
bathroom|room_cat|used_for:washing|part:tub or shower and a sink
living_room|room_cat|used_for:gathering and relaxing|part:a couch and tv
dining_room|room_cat|used_for:shared meals|part:a table and chairs
garage|room_cat|used_for:parking a car at home
attic|room_cat|used_for:storing old things|feature:the space under the roof
basement|room_cat|used_for:cool storage below|feature:the room under the house
hallway|room_cat|used_for:walking between rooms
office_room|room_cat|used_for:focus work|part:a desk and chair
laundry_room|room_cat|used_for:washing clothes at home
pantry|room_cat|used_for:storing food shelves
closet|room_cat|used_for:hiding clothes and clutter
nursery|room_cat|used_for:caring for a baby
classroom|room_cat|used_for:lessons at desks
gym|room_cat|used_for:exercise equipment
balcony|room_cat|used_for:open-air standing at height
paris|landmark|feature:the eiffel tower and broad boulevards|habitat:france
eiffel_tower|landmark|feature:an iron lattice over paris|shape:tall and tapering
big_ben|landmark|feature:london's clock tower
tower_bridge|landmark|feature:a thames bridge that opens
stonehenge|landmark|feature:a ring of standing stones|habitat:england
colosseum|landmark|feature:rome's old amphitheater|habitat:italy
leaning_tower|landmark|feature:a tower that leans in pisa
acropolis|landmark|feature:athens' hilltop temples|habitat:greece
sphinx_monument|landmark|feature:a lion with a human head at giza|habitat:egypt
great_wall|landmark|feature:a wall miles long across ridges|habitat:china
forbidden_city|landmark|feature:beijing's imperial palace|habitat:china
taj_mahal|landmark|feature:a white marble tomb in agra|habitat:india
machu_picchu|landmark|feature:an inca city in the clouds|habitat:peru
easter_island|landmark|feature:giant stone heads on a remote island
statue_of_liberty|landmark|feature:a copper lady with a torch|habitat:new york
golden_gate|landmark|feature:a red suspension bridge|habitat:san francisco
grand_canyon|landmark|feature:a mile-deep river gorge|habitat:arizona
niagara_falls|landmark|feature:thundering falls between two countries
mount_rushmore|landmark|feature:four presidents in rock
times_square|landmark|feature:glowing screens in new york
central_park|landmark|feature:a green rectangle in manhattan
vatican|landmark|feature:the smallest country and st peter's
petra|landmark|feature:a city carved in rose rock|habitat:jordan
angkor_wat|landmark|feature:a vast temple complex|habitat:cambodia
mount_fuji|landmark|feature:a perfect volcano cone|habitat:japan
burj_khalifa|landmark|feature:the tallest tower on earth|habitat:dubai
sydney_opera|landmark|feature:white shells over the harbor|habitat:australia
sahara|landmark|feature:the largest hot desert|habitat:north africa
amazon_river|landmark|feature:the greatest river by flow|habitat:south america
mount_everest|landmark|feature:the highest point on earth|habitat:the himalayas
mountain|landform|feature:rises far above the land|trait:cold at the top
hill|landform|feature:a gentle rise of land
valley|landform|feature:low land between hills|shape:a long hollow
canyon|landform|feature:a deep gorge carved by a river
plateau|landform|feature:high flat land
plain|landform|feature:wide open flat land
desert|landform|feature:almost no rain falls
ocean|landform|feature:salt water covering most of the earth
sea|landform|feature:salt water beside land
lake|landform|feature:water ringed by land
river|landform|feature:water running to the sea|trait:currents
stream|landform|feature:a small running water
waterfall|landform|feature:water dropping over a cliff
glacier|landform|feature:a slow river of ice
volcano|landform|feature:erupts lava and ash
island|landform|feature:land ringed by water
peninsula|landform|feature:land almost ringed by water
beach|landform|feature:sand meeting the sea
cliff|landform|feature:a sheer rock face
cave|landform|feature:a hollow in the rock|trait:dark inside
forest|landform|feature:trees as far as you see
jungle|landform|feature:dense tropical forest
swamp|landform|feature:soft wet ground and trees
meadow|landform|feature:open grass and wildflowers
tundra|landform|feature:frozen ground and low plants
reef|landform|feature:a ridge of coral under the sea
geyser|landform|feature:shoots hot water skyward
hot_spring|landform|feature:warm water rising from the ground
dune|landform|feature:a hill of sand that wanders
delta|landform|feature:where a river splits to the sea
fjord|landform|feature:a deep sea inlet between cliffs
wood|material|made_of:tree trunks|used_for:building and burning
metal|material|trait:strong and shiny|used_for:structures and tools
steel|material|made_of:iron with carbon|trait:very strong
iron|material|trait:heavy magnetic metal
copper|material|trait:red metal that carries current
aluminum|material|trait:light metal
gold|material|trait:precious yellow metal that never rusts
silver|material|trait:shiny precious metal
bronze|material|made_of:copper and tin
brass|material|made_of:copper and zinc
plastic|material|made_of:oil|trait:molds into any shape
glass|material|made_of:melted sand|trait:clear and brittle
ceramic|material|made_of:fired clay|trait:hard and brittle
clay|material|trait:soft earth that holds its shape when fired
concrete|material|made_of:cement and stone|used_for:foundations
brick|material|made_of:fired clay blocks|used_for:walls
marble|material|trait:stone that polishes to a glow|used_for:statues
granite|material|trait:hard speckled stone
stone|material|trait:the earth's own building block
sand|material|made_of:tiny rock grains
gravel|material|made_of:small stones
cement|material|used_for:binding stone together
rubber|material|trait:stretches and springs back|made_of:tree sap or oil
paper|material|made_of:pressed wood fibers|used_for:writing
cardboard|material|made_of:thick paper layers|used_for:boxes
wool|material|made_of:sheep fleece|used_for:warm cloth
cotton|material|made_of:a plant's fluffy boll|used_for:cloth
silk|material|made_of:silkworm thread|trait:smooth and shining
leather|material|made_of:tanned animal hide|trait:tough and flexible
fur|material|made_of:animal hair|used_for:warmth
feather|material|made_of:bird plumage|trait:light as air
bamboo_wood|material|trait:grows fast and bends strong
cork|material|made_of:tree bark|trait:floats and springs
foam|material|trait:full of air bubbles
wax|material|trait:melts warm, hard when cool
chalk|material|used_for:writing on boards
ink|material|used_for:writing in color
paint|material|used_for:coloring surfaces|made_of:pigment and binder
varnish|material|used_for:shining and sealing wood
oil|material|used_for:fuel and lubrication|made_of:ancient buried life
gas|material|used_for:fuel and cooking
coal|material|made_of:ancient forests pressed to black stone
charcoal|material|used_for:hot clean burning
bread|food_cat|made_of:flour, water and yeast|taste:warm and plain
rice_food|food_cat|role:the staple of half the earth|trait:small white grains
pasta|food_cat|made_of:wheat dough|shape:ribbons and tubes
noodles|food_cat|made_of:dough pulled thin|used_for:slurping soups
flour|food_cat|made_of:ground grain|used_for:baking
sugar|food_cat|taste:sweet|made_of:cane or beets
salt|food_cat|taste:salty|made_of:sea or mines
pepper|food_cat|taste:sharp and hot
honey|food_cat|made_of:bees from flowers|taste:sweet and floral
butter|food_cat|made_of:churned cream|trait:melts on warm toast
cheese|food_cat|made_of:aged milk|taste:from mild to sharp
milk|drink|made_of:cows|trait:white and nourishing
yogurt|food_cat|made_of:fermented milk|taste:tangy
egg|food_cat|made_of:hens|part:shell, white and yolk
meat|food_cat|made_of:animals raised for food
chicken_food|food_cat|role:the most eaten meat
beef|food_cat|made_of:cattle
pork|food_cat|made_of:pigs
fish_food|food_cat|made_of:caught and farmed fish
bacon|food_cat|made_of:cured pork|taste:salty and smoky
sausage|food_cat|made_of:spiced meat in a skin
ham|food_cat|made_of:cured pork leg
steak|food_cat|made_of:beef cut thick
apple|food_cat|taste:crisp and sweet|color:red or green
banana|food_cat|taste:sweet and soft|color:yellow
orange_fruit|food_cat|taste:sweet and tart|color:orange|part:a peel full of scent
lemon|food_cat|taste:sour|color:yellow
lime|food_cat|taste:sour and green
grape|food_cat|taste:sweet|used_for:raisins and wine
strawberry|food_cat|taste:sweet with seeds outside|color:red
blueberry|food_cat|taste:sweet and small|color:blue
raspberry|food_cat|taste:tart and delicate
watermelon|food_cat|feature:mostly sweet water|color:green outside, red inside
melon|food_cat|feature:sweet and cool inside
peach|food_cat|taste:soft and sweet|feature:fuzzy skin
pear|food_cat|taste:sweet and grainy
cherry|food_cat|taste:sweet with a pit
pineapple|food_cat|feature:a crown of leaves|taste:sweet and sharp
mango|food_cat|taste:golden sweetness
coconut|food_cat|part:milk and flesh inside a husk
kiwi_fruit|food_cat|feature:brown outside, green inside
avocado|food_cat|taste:buttery|part:a big pit
tomato|food_cat|trait:eaten like a vegetable, born a fruit|color:red
carrot|food_cat|color:orange|part:a root
potato|food_cat|part:a root that grows underground|used_for:fries and mash
onion|food_cat|feature:makes eyes water|part:a layered bulb
garlic|food_cat|trait:pungent|part:clove inside a bulb
broccoli|food_cat|color:green|shape:a little tree
cauliflower|food_cat|color:white|shape:a tight head
cabbage|food_cat|shape:layers wrapped tight
spinach|food_cat|trait:leafy and iron-rich
lettuce|food_cat|used_for:salads|trait:crisp leaves
corn_food|food_cat|part:kernels in rows|color:yellow
peas|food_cat|part:round green seeds in pods
beans|food_cat|trait:protein-rich seeds
lentils|food_cat|trait:small flat seeds
mushroom_food|food_cat|trait:a fungus you can eat|shape:cap and stem
olive|food_cat|used_for:oil and snacking
pickles|food_cat|made_of:cucumbers in brine|taste:sour and crisp
cucumber|food_cat|trait:cool and crisp
pumpkin|food_cat|feature:hollows into lanterns|color:orange
soup|dish|trait:served hot in a bowl|made_of:broth and ingredients
salad|dish|made_of:raw greens and toppings
sandwich|dish|made_of:fillings between bread
hamburger|dish|made_of:a patty in a bun|part:lettuce, cheese and sauce
hotdog|dish|made_of:a sausage in a split bun
pizza|dish|made_of:dough, sauce and cheese|feature:baked flat and sliced
taco|dish|made_of:fillings folded in a tortilla
burrito|dish|made_of:fillings rolled in a tortilla
sushi|dish|made_of:rice, fish and seaweed|feature:rolled and sliced
pancake|dish|trait:flat, round and golden|taste:sweet with syrup
waffle|dish|feature:a grid of deep pockets
omelette|dish|made_of:beaten eggs cooked flat
fries|dish|made_of:fried potato sticks|taste:salty and crisp
chips|dish|made_of:thin fried potatoes|trait:bagged and crunchy
popcorn|dish|made_of:corn that bursts with heat
ice_cream|dish|taste:cold and sweet|made_of:frozen cream
cake|dish|used_for:birthdays|made_of:flour, sugar and frosting
pie|dish|part:a crust around a filling
cookie|dish|taste:sweet and chewy|made_of:dough with chips
donut|dish|shape:a ring with a hole|trait:fried and glazed
chocolate|dish|made_of:cacao|taste:rich and sweet
candy|dish|taste:sweet|made_of:sugar
pudding|dish|trait:soft and spoonable
stew|dish|trait:slow-cooked and hearty
curry|dish|made_of:spiced sauce|trait:from mild to fiery
roast|dish|trait:cooked dry in the oven
barbecue|dish|trait:smoked low and slow|feature:backyard ritual
breakfast|dish|role:the first meal of the day
lunch|dish|role:the midday meal
dinner|dish|role:the evening meal
snack|dish|role:a bite between meals
water|drink|trait:clear and tasteless|feature:everything needs it
juice|drink|made_of:squeezed fruit
coffee|drink|made_of:roasted beans|taste:bitter and waking|trait:served hot
tea|drink|made_of:steeped leaves|trait:the world's quiet drink
soda|drink|trait:fizzy and sweet
lemonade|drink|made_of:lemons, sugar and water
milkshake|drink|made_of:blended milk and ice cream
smoothie|drink|made_of:blended fruit
cocoa|drink|made_of:chocolate and milk|trait:warm winter comfort
beer|drink|made_of:fermented grain
wine|drink|made_of:fermented grapes
lemon_tea|drink|made_of:tea with lemon
engineer|role_cat|role:builds and fixes machines
doctor|role_cat|role:heals the sick
nurse|role_cat|role:cares for patients
teacher|role_cat|role:teaches children and students
farmer|role_cat|role:grows food and tends animals
baker|role_cat|role:bakes bread and cakes
butcher|role_cat|role:cuts and sells meat
chef|role_cat|role:runs a kitchen
waiter|role_cat|role:serves tables
barber|role_cat|role:cuts hair
tailor|role_cat|role:mends and makes clothes
carpenter|role_cat|role:builds with wood
plumber|role_cat|role:fixes water pipes
electrician|role_cat|role:wires buildings safely
mechanic|role_cat|role:repairs engines
pilot|role_cat|role:flies planes
sailor|role_cat|role:works at sea
firefighter|role_cat|role:fights fires and saves people
police_officer|role_cat|role:keeps the peace
soldier|role_cat|role:defends the country
scientist|role_cat|role:runs experiments to learn
mathematician|role_cat|role:works with numbers and proofs
astronomer|role_cat|role:studies stars and planets
biologist|role_cat|role:studies living things
geologist|role_cat|role:studies rock and earth
chemist|role_cat|role:studies matter and reactions
physicist|role_cat|role:studies motion, light and force
programmer|role_cat|role:writes software
artist|role_cat|role:makes art
painter|role_cat|role:paints pictures
sculptor|role_cat|role:carves statues
musician|role_cat|role:plays music
singer|role_cat|role:sings songs
actor|role_cat|role:acts in stories on stage and screen
writer|role_cat|role:writes books
poet|role_cat|role:writes poems
journalist|role_cat|role:reports the news
photographer|role_cat|role:catches pictures
dentist|role_cat|role:cares for teeth
veterinarian|role_cat|role:heals animals
architect|role_cat|role:designs buildings
judge|role_cat|role:decides cases in court
lawyer|role_cat|role:argues cases in court
librarian|role_cat|role:tends the library
miner|role_cat|role:digs ore and coal underground
fisherman|role_cat|role:catches fish for a living
hunter|role_cat|role:tracks wild game
shepherd|role_cat|role:tends sheep
guard|role_cat|role:watches and protects
mail_carrier|role_cat|role:delivers letters door to door
bus_driver|role_cat|role:drives the bus route
taxi_driver|role_cat|role:drives people for fare
conductor|role_cat|role:leads an orchestra
dancer|role_cat|role:dances on stage
athlete|role_cat|role:competes in sport
coach|role_cat|role:trains athletes
referee|role_cat|role:enforces the rules of the game
inventor|role_cat|role:builds new things that never existed
explorer|role_cat|role:goes where few have gone
king|role_cat|role:rules a kingdom
queen|role_cat|role:rules beside or instead of a king
president|role_cat|role:leads a country
mayor|role_cat|role:leads a city
head|body_part|part:brain, eyes, ears, nose and mouth
brain|body_part|feature:thinks and remembers
eye|body_part|used_for:seeing|part:two of them
ear|body_part|used_for:hearing|part:two of them
nose|body_part|used_for:smelling and breathing
mouth|body_part|used_for:eating and speaking
tooth|body_part|used_for:chewing|part:enamel outside
tongue|body_part|used_for:tasting and talking
lip|body_part|part:two of them around the mouth
chin|body_part|part:below the mouth
cheek|body_part|part:beside the nose
forehead|body_part|part:above the eyes
eyebrow|body_part|feature:shields the eyes
eyelash|body_part|feature:keeps dust from the eye
neck|body_part|part:joins head and shoulders
shoulder|body_part|part:two of them|used_for:carrying
arm|body_part|part:from shoulder to hand
elbow|body_part|feature:bends the arm
wrist|body_part|part:joins arm and hand
hand|body_part|part:fingers and a thumb|used_for:grasping
finger|body_part|part:five per hand
thumb|body_part|feature:the gripping finger
fingernail|body_part|feature:guards the fingertips
chest|body_part|part:heart and lungs inside
heart|body_part|feature:pumps blood all day
lung|body_part|used_for:breathing air|part:two of them
rib|body_part|feature:cages the chest
stomach|body_part|used_for:digesting food
back|body_part|part:spine runs down it
spine|body_part|feature:the body's stack of bones
waist|body_part|part:between ribs and hips
hip|body_part|part:joins leg to body
leg|body_part|part:from hip to foot
knee|body_part|feature:bends the leg
ankle|body_part|part:joins leg and foot
foot|body_part|part:toes and a sole|used_for:walking
toe|body_part|part:five per foot
skin|body_part|feature:covers the whole body
hair|body_part|feature:grows on the head
bone|body_part|feature:the frame under the flesh
muscle|body_part|feature:moves the body by pulling
blood|body_part|feature:carries oxygen everywhere
lung_bronchi|body_part|part:airways inside the lungs
second|time_cat|trait:the smallest common beat of time
minute|time_cat|trait:sixty seconds
hour|time_cat|trait:sixty minutes
day|time_cat|trait:twenty-four hours, one spin of the earth
night|time_cat|trait:the dark half of a day
week|time_cat|trait:seven days
month|time_cat|trait:about four weeks, one lap of the moon
year|time_cat|trait:twelve months, one lap of the sun
decade|time_cat|trait:ten years
century|time_cat|trait:a hundred years
morning|time_cat|trait:the early part of the day
afternoon|time_cat|trait:between noon and evening
evening|time_cat|trait:the winding-down of the day
midnight|time_cat|trait:the middle of the night
noon|time_cat|trait:the sun's highest point
dawn|time_cat|trait:the first light of day
dusk|time_cat|trait:the last light of day
birthday|time_cat|feature:once a year, cakes and candles
holiday|time_cat|feature:a day off with meaning
weekend|time_cat|trait:saturday and sunday
chess|game_cat|feature:sixteen pieces, one king to trap|part:a checkered board
checkers|game_cat|feature:jumps and kings on a simple board
tag|game_cat|feature:chasing and touching
hide_and_seek|game_cat|feature:hiding while someone counts
tic_tac_toe|game_cat|feature:three in a row wins
poker|game_cat|feature:bets and bluffs on five cards
bridge_game|game_cat|feature:four players, two partnerships
dominoes|game_cat|feature:matching ends of dotted tiles
darts|game_cat|feature:throws at a numbered board
billiards|game_cat|feature:cue balls on green felt
bowling|sport|feature:ten pins down a polished lane
soccer|sport|feature:two goals, one ball, no hands
basketball|sport|feature:hoops and dribbling|part:a high net ring
baseball|sport|feature:bat, ball and four bases
tennis|sport|feature:rallies over a net|part:a strung racket
volleyball|sport|feature:spiking over a high net
golf|sport|feature:tiny ball, huge course|part:clubs of many lofts
hockey|sport|feature:pucks and sticks on ice
rugby|sport|feature:an oval ball carried forward
cricket|sport|feature:batting for days in white
boxing|sport|feature:gloves and rounds
swimming|sport|feature:racing through water
running|sport|feature:the oldest race there is
cycling|sport|feature:racing on two wheels
skiing|sport|feature:down snow on long boards
snowboarding|sport|feature:one board, sideways stance
skating|sport|feature:blades on ice
gymnastics|sport|feature:flips, beams and rings
track_and_field|sport|feature:running, jumping and throwing
archery_sport|sport|feature:hitting rings with arrows
fencing|sport|feature:dueling with thin blades
judo|sport|feature:throws and holds
karate|sport|feature:strikes and blocks
surfing|sport|feature:riding waves on a board
red|color_cat|trait:the color of blood and stop signs
blue|color_cat|trait:the color of the deep sea and sky
green|color_cat|trait:the color of leaves and go signs
yellow|color_cat|trait:the color of the sun and lemons
orange_color|color_cat|trait:between red and yellow
purple|color_cat|trait:the old royal color
pink|color_cat|trait:a soft pale red
brown|color_cat|trait:the color of earth and wood
black|color_cat|trait:absorbs all light
white|color_cat|trait:reflects all light
gray|color_cat|trait:between black and white
violet|color_cat|trait:the edge of the rainbow
circle|shape_cat|shape:round with no corners
square|shape_cat|shape:four equal sides
triangle|shape_cat|shape:three sides
rectangle|shape_cat|shape:four sides, two long two short
oval|shape_cat|shape:a stretched circle
star_shape|shape_cat|shape:points radiating out
heart_shape|shape_cat|shape:two curves and a point
diamond|shape_cat|shape:four sides tilted square
hexagon|shape_cat|shape:six sides
spiral|shape_cat|shape:curves winding outward
cube|shape_cat|shape:a square box in three dimensions
sphere|shape_cat|shape:a ball in three dimensions
book|book_cat|part:pages bound at a spine
novel|book_cat|feature:a long invented story
dictionary|book_cat|feature:every word and its meaning
encyclopedia|book_cat|feature:knowledge by subject, a to z
atlas|book_cat|feature:maps of the whole world
textbook|book_cat|feature:lessons by chapter
notebook|book_cat|used_for:notes and sketches
comic|book_cat|feature:panels and speech bubbles
poetry_book|book_cat|feature:verse and rhythm
cookbook|book_cat|feature:recipes step by step
magazine|book_cat|feature:glossy pages, new issues
newspaper|book_cat|feature:the day's news in print
calendar|book_cat|feature:the year on twelve pages
map|book_cat|feature:the world drawn small
letter|book_cat|used_for:sent messages on paper
diary|book_cat|feature:a private day-by-day record
"""

# ============================ VOCAB — verbs ====================================
# irregulars: base -> (past, ing); everything else is regular and gets forms
# from the same orthography rules the organism can discover (dsl.reg_*).
IRREG_VERBS = {
    "go": ("went", "going", "goes"), "be": ("was", "being", "is"),
    "have": ("had", "having", "has"), "do": ("did", "doing", "does"),
    "say": ("said", "saying"), "make": ("made", "making"),
    "take": ("took", "taking"), "come": ("came", "coming"), "see": ("saw", "seeing"),
    "know": ("knew", "knowing"), "get": ("got", "getting"), "give": ("gave", "giving"),
    "find": ("found", "finding"), "think": ("thought", "thinking"),
    "tell": ("told", "telling"), "feel": ("felt", "feeling"),
    "leave": ("left", "leaving"), "put": ("put", "putting"),
    "bring": ("brought", "bringing"), "run": ("ran", "running"),
    "write": ("wrote", "writing"), "sit": ("sat", "sitting"),
    "stand": ("stood", "standing"), "lose": ("lost", "losing"),
    "pay": ("paid", "paying"), "meet": ("met", "meeting"),
    "sleep": ("slept", "sleeping"), "speak": ("spoke", "speaking"),
    "read": ("read", "reading"), "grow": ("grew", "growing"),
    "walk_": None,  # placeholder removed below
}
IRREG_VERBS.pop("walk_", None)
IRREG_VERBS.update({
    "win": ("won", "winning"), "buy": ("bought", "buying"),
    "send": ("sent", "sending"), "build": ("built", "building"),
    "fall": ("fell", "falling"), "cut": ("cut", "cutting"),
    "reach": ("reached", "reaching"), "remain": ("remained", "remaining"),
    "keep": ("kept", "keeping"), "hold": ("held", "holding"),
    "wear": ("wore", "wearing"), "drive": ("drove", "driving"),
    "break": ("broke", "breaking"), "eat": ("ate", "eating"),
    "drink": ("drank", "drinking"), "swim": ("swam", "swimming"),
    "fly": ("flew", "flying"), "ride": ("rode", "riding"),
    "sing": ("sang", "singing"), "ring": ("rang", "ringing"),
    "begin": ("began", "beginning"), "choose": ("chose", "choosing"),
    "draw": ("drew", "drawing"), "lead": ("led", "leading"),
    "teach": ("taught", "teaching"), "learn": ("learnt", "learning"),
    "hear": ("heard", "hearing"), "fight": ("fought", "fighting"),
    "catch": ("caught", "catching"), "throw": ("threw", "throwing"),
    "shake": ("shook", "shaking"), "sweep": ("swept", "sweeping"),
    "creep": ("crept", "creeping"), "feel_": None, "burn": ("burnt", "burning"),
    "dream": ("dreamt", "dreaming"), "mean": ("meant", "meaning"),
    "deal": ("dealt", "dealing"), "lay": ("laid", "laying"),
    "lie": ("lay", "lying"), "rise": ("rose", "rising"),
    "fall_": None, "hide": ("hid", "hiding"), "bite": ("bit", "biting"),
    "stick": ("stuck", "sticking"), "strike": ("struck", "striking"),
    "spread": ("spread", "spreading"), "swell": ("swelled", "swelling"),
    "flee": ("fled", "fleeing"), "seek": ("sought", "seeking"),
    "spend": ("spent", "spending"), "weave": ("wove", "weaving"),
    "dig": ("dug", "digging"), "hang": ("hung", "hanging"),
    "wind": ("wound", "winding"), "grind": ("ground", "grinding"),
    "shoot": ("shot", "shooting"), "slide": ("slid", "sliding"),
    "steal": ("stole", "stealing"), "tear": ("tore", "tearing"),
    "wake": ("woke", "waking"), "forgive": ("forgave", "forgiving"),
    "forget": ("forgot", "forgetting"), "freeze": ("froze", "freezing"),
    "speak_": None, "steal_": None, "swear": ("swore", "swearing"),
    "swing": ("swung", "swinging"), "bleed": ("bled", "bleeding"),
    "breed": ("bred", "breeding"), "cast": ("cast", "casting"),
    "cost": ("cost", "costing"), "fit": ("fitted", "fitting"),
    "hurt": ("hurt", "hurting"), "let": ("let", "letting"),
    "shut": ("shut", "shutting"), "split": ("split", "splitting"),
    "spit": ("spat", "spitting"), " upset": None,
})
for _k in [k for k, v in list(IRREG_VERBS.items()) if v is None or k.endswith("_")]:
    IRREG_VERBS.pop(_k, None)
IRREG_VERBS.pop(" upset", None)

VERBS = """
walk run jump climb swim fly crawl slide hop skip march jog sprint
dance sing whistle hum shout whisper talk speak chat laugh cry smile frown
greet wave nod shake bow hug kiss wave_ point stare glance watch look see
listen hear smell taste touch feel_ hold grip grab pinch squeeze pat tap
push pull lift carry drag drop throw catch toss roll spin turn twist bend
fold tear_ cut paste tie_ wrap open close lock unlock start stop begin end
finish continue repeat try_ fail_ succeed win lose draw paint write read
spell count add subtract multiply divide measure weigh compare sort group
match mix stir pour spill fill empty pour_ drain wash rinse dry scrub wipe
sweep mop dust polish shine clean dirty_ tidy organize arrange stack pile
build make create fix_ repair break smash crack bend_ stretch squeeze_
press squash bounce bounce_ balance topple lean tilt support hang drape
plant grow_ water_ prune harvest pick_ dig_ bury_ plant_ rake_ mow sow
bake boil fry roast grill steam simmer melt freeze chill warm_ cool_ heat
cook stir_ knead taste_ serve eat drink_ chew swallow bite_ sip_ gulp
breathe inhale exhale cough sneeze yawn blink wink stare_ sleep_ wake_ dream
rest relax stretch_ snore nap doze snuggle cuddle snuggle_ stroke pet_
chase flee_ hunt stalk pounce bite scratch groom peck perch nest roost
bark meow moo oink neigh bleat crow_ quack honk chirp tweet howl growl
purr hiss buzz_ drone croak ribbit hoot_ trumpet_ roar squeak squeal
think know_ believe wonder guess_ imagine pretend remember forget recall
learn_ teach_ study practice drill repeat_ memorize understand realize
decide choose_ pick_ prefer want need_ wish hope dream_ plan intend try_
mean_ imply suggest_ propose_ agree disagree argue debate question_ answer
ask tell_ explain describe define name_ call_ label_ mention_ state_ claim
say_ speak_ mutter mumble shout_ yell scream_ cheer_ boo_ applaud clap
help_ serve_ share_ give_ take_ receive offer_ accept refuse deny_ admit
allow_ permit forbid_ ban_ block_ allow_ borrow lend_ keep_ save_ spend_
buy_ sell_ trade_ swap_ pay_ owe_ earn_ cost_ afford_ rent_ hire_ fire_
work_ rest_ play_ perform_ act_ rehearse audition compete_ race_ exercise
train_ coach_ lead_ follow_ guide_ direct_ manage_ organize_ plan_ schedule
wait_ hurry_ rush_ slow_ pause_ resume_ delay_ cancel_ postpone_ skip_
arrive_ depart_ leave_ enter_ exit_ return_ stay_ remain_ wander_ roam_
travel_ commute_ drive_ ride_ sail_ fly_ land_ takeoff park_ steer_ brake
accelerate turn_ swerve_ reverse_ park_ dock_ anchor_ drift_ float_ sink
dive_ plunge_ splash_ soak_ drench_ dampen_ evaporate condense freeze_ thaw
melt_ burn_ blaze_ ignite_ extinguish smolder glow_ flicker sparkle_ shimmer
glow_ beam_ radiate_ reflect_ absorb_ block_ filter_ dim_ brighten_ darken
color_ dye_ bleach_ fade_ stain_ paint_ sketch_ doodle_ trace_ outline
shade_ highlight_ erase_ correct_ edit_ revise_ polish_ refine_ improve
worsen_ damage_ harm_ hurt_ heal_ cure_ treat_ soothe_ comfort_ console
encourage_ inspire_ motivate_ praise_ scold_ punish_ reward_ forgive_
trust_ doubt_ suspect_ believe_ doubt_ question_ wonder_ doubt_ admire
respect_ adore_ love_ like_ enjoy_ hate_ dislike_ despise_ resent_ envy_
miss_ long_ desire_ crave_ prefer_ choose_ select_ elect_ appoint_ name_
rank_ rate_ score_ grade_ judge_ evaluate_ assess_ estimate_ predict_
forecast_ calculate_ compute_ solve_ figure_ derive_ conclude_ infer_
deduce_ reason_ logic_ argue_ justify_ prove_ verify_ check_ test_ inspect
examine_ observe_ notice_ spot_ detect_ discover_ invent_ design_ create_
construct_ assemble_ disassemble_ install_ remove_ replace_ swap_ upgrade
downgrade_ adjust_ tune_ calibrate_ align_ level_ plumb_ square_ center
"""
for _k in [k for k, v in list(IRREG_VERBS.items()) if v is None or k.endswith("_")]:
    IRREG_VERBS.pop(_k, None)


def verb_concepts():
    out, seen = [], set()
    # every irregular in the table becomes a lesson verb, always
    words = dict.fromkeys([w.strip("_") for w in VERBS.split()]
                          + list(IRREG_VERBS.keys()))
    for w in words:
        if w in seen:
            continue
        seen.add(w)
        if w in IRREG_VERBS:
            v = IRREG_VERBS[w]
            past, ing = v[0], v[1]
            third = v[2] if len(v) > 2 and v[2] else reg_third(w)
        else:
            past, ing = reg_past(w), reg_ing(w)
            third = reg_third(w)
        out.append({"id": "verb_%s" % w, "kind": "verb_form", "words": [w],
                    "attrs": {"third": third, "past": past, "ing": ing},
                    "relations": [{"to": "verb", "rel": "is-a"}]})
    return out


# ============================ VOCAB — adjectives ===============================
ADJECTIVES = """
big small tall short long wide narrow thick thin heavy light_ fast slow
hot cold warm cool wet dry_ hard soft rough smooth sharp dull_ shiny dull
bright dark_ loud quiet_ noisy silent clean_ dirty fresh stale new old_
young_ ancient modern strong weak tough fragile delicate sturdy flimsy
rich poor_ rich_ wealthy hungry thirsty full empty open shut_ closed
happy sad angry calm excited bored tired_ awake sleepy sleepy_ grumpy
cheerful gloomy serious silly funny_ joking honest_ honest shy_ bold brave
scared brave_ kind_ cruel gentle_ mean_ polite rude_ friendly_ lonely
proud_ humble_ jealous_ greedy generous_ selfish_ lazy_ busy_ eager keen
smart_ clever wise_ foolish_ silly_ dumb brilliant genius_ quick_ slow_
early late_ soon punctual_ quick rapid gradual sudden_ steady_ shaky
smooth_ bumpy_ even_ uneven_ level_ crooked_ straight curved_ twisted
round square_ flat_ pointy_ round_ oval_ spiral_ wavy_ zigzag loose_ tight
loose stiff_ flexible_ rigid_ elastic_ sticky_ slippery_ greasy_ oily dry
sour sweet_ bitter_ salty_ spicy_ bland_ tasty_ delicious_ yummy_ gross
juicy_ ripe_ raw_ rotten_ fresh_ frozen_ boiled_ fried_ baked_ mashed
beautiful_ pretty_ handsome_ ugly_ cute_ elegant_ fancy_ plain_ simple_
complex_ fancy_ ornate_ bare_ plain grand_ modest_ cozy_ cramped_ roomy
huge tiny_ giant_ massive_ enormous_ microscopic_ giant_ little_ medium
deep_ shallow_ high_ low_ near_ far_ close_ distant_ nearby_ remote
loud_ deafening_ piercing_ soft_ gentle faint_ muffled_ crisp_ muffled
sunny_ rainy_ cloudy_ foggy_ stormy_ windy_ calm_ still_ wild_ mild_ harsh
lucky_ unlucky_ strange_ weird_ odd_ normal_ usual_ unusual_ common_ rare_
easy_ hard_ difficult_ simple_ tricky_ puzzling_ obvious_ clear_ murky
safe_ dangerous_ risky_ secure_ scary_ creepy_ cozy_ snug_ warm_ chilly
real_ fake_ genuine_ artificial_ natural_ man-made raw_ cooked_ ripe_
alive_ dead_ living_ dying_ awake_ asleep_ drunk_ sober_ sick_ healthy_
ill_ well_ weak_ faint_ dizzy_ blind_ deaf_ mute_ numb_ sore_ itchy_
sweet sour bitter salty savory spicy mild_ hot_ tepid_ icy_ freezing
boiling humid_ arid_ dusty_ muddy_ muddy_ soggy_ damp_ moist_ parched
"""
ADJECTIVES = "\n".join(sorted(set(w for w in ADJECTIVES.split() if not w.endswith("_"))))


def adj_concepts():
    return [{"id": "adj_%s" % w, "kind": "adj_form", "words": [w],
             "relations": [{"to": "adjective", "rel": "is-a"}]}
            for w in ADJECTIVES.splitlines()]


# ============================ VOCAB — everyday nouns ===========================
NOUNS = """
dog cat bird fish horse cow pig sheep goat chicken duck rabbit mouse rat
hamster squirrel fox wolf bear deer lion tiger elephant giraffe zebra
monkey gorilla kangaroo panda snake frog turtle spider bee ant butterfly
boy girl man woman baby child family mother father sister brother son
daughter friend neighbor teacher doctor nurse farmer baker chef driver
pilot sailor soldier police firefighter dentist artist singer dancer
writer student player coach judge lawyer king queen president mayor
house home apartment room kitchen bedroom bathroom door window wall floor
roof ceiling stairs garden yard fence gate driveway porch garage
table chair bed sofa desk shelf box basket bag backpack bottle cup plate
bowl spoon fork knife pot pan kettle teapot mirror clock lamp candle
phone computer laptop tablet camera television radio printer keyboard
car bus truck train bicycle boat ship airplane rocket wheel engine
street road sidewalk highway bridge tunnel park playground beach forest
mountain river lake ocean island desert field hill valley cave farm
city town village country world earth sky sun moon star cloud rain snow
wind storm thunder lightning rainbow fog shadow light_ darkness heat cold
morning afternoon evening night dawn dusk midnight noon day week month
year hour minute second today tomorrow yesterday birthday holiday
apple banana orange lemon grape strawberry watermelon peach pear cherry
bread rice pasta egg milk cheese butter sugar salt honey meat chicken
fish_ beef pork soup salad sandwich pizza hamburger cake cookie pie
ice cream chocolate candy coffee tea juice water soda lemonade popcorn
book page letter story poem song word sentence question answer name
number letter_ color shape line circle square triangle box_ dot
game toy ball doll kite puzzle card dice gift present party game_
school class lesson homework test grade desk chalk pencil pen crayon
paper page_ eraser ruler scissors glue paint_ brush_ music_ drum_ bell_
shirt pants dress shoe sock hat coat glove scarf belt button pocket
zipper thread needle_ fabric_ color_ pattern_ size_ price_ money_ coin
dream_ idea_ thought_ secret_ wish_ promise_ lie_ truth_ story_ joke_
question_ reason_ plan_ choice_ chance_ luck_ future_ past_ present_
love_ fear_ hope_ joy_ anger_ pride_ shame_ trust_ doubt_ courage_
"""
NOUNS = "\n".join(sorted(set(w for w in NOUNS.split() if not w.endswith("_"))))


def noun_concepts():
    out = []
    for w in NOUNS.splitlines():
        if not w:
            continue
        out.append({"id": "noun_%s" % w, "kind": "noun_form", "words": [w],
                    "attrs": {"plural": plural(w)},
                    "relations": [{"to": "noun", "rel": "is-a"}]})
    return out


# ============================ SENTENCE GRAMMAR =================================
def sent_grammar_concepts():
    return [
        {"id": "sentence_grammar", "kind": "domain", "words": ["sentence grammar"],
         "attrs": {"what": "how sentences are built, asked, denied and timed"}},
        # aux tables — agreement physics the organism was TAUGHT, never coded
        {"id": "aux_do", "kind": "aux_table", "words": ["do", "does", "did"],
         "attrs": {"i": "do", "you": "do", "he": "does", "she": "does",
                   "it": "does", "we": "do", "they": "do",
                   "singular": "does", "plural": "do"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "aux_be", "kind": "aux_table", "words": ["am", "is", "are", "be"],
         "attrs": {"i": "am", "you": "are", "he": "is", "she": "is",
                   "it": "is", "we": "are", "they": "are",
                   "singular": "is", "plural": "are"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "aux_will", "kind": "aux_table", "words": ["will", "shall"],
         "attrs": {"i": "will", "you": "will", "he": "will", "she": "will",
                   "it": "will", "we": "will", "they": "will",
                   "singular": "will", "plural": "will"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "contractions", "kind": "aux_table", "words": ["contraction"],
         "attrs": {"do not": "don't", "does not": "doesn't", "did not": "didn't",
                   "is not": "isn't", "are not": "aren't", "am not": "am not",
                   "was not": "wasn't", "were not": "weren't",
                   "will not": "won't", "would not": "wouldn't",
                   "can not": "can't", "cannot": "can't", "could not": "couldn't",
                   "should not": "shouldn't", "have not": "haven't",
                   "has not": "hasn't", "had not": "hadn't"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        # function words
        {"id": "pronoun", "kind": "word_class", "words": ["pronoun"],
         "attrs": {"singular": "i you he she it", "plural": "we they",
                   "does": "stands in for a name"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "determiner", "kind": "word_class", "words": ["determiner", "article"],
         "attrs": {"list": "a an the", "does": "points at a noun"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "preposition", "kind": "word_class", "words": ["preposition"],
         "attrs": {"list": "in on at by with from to under over near",
                   "does": "situates a thing in place or time"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "conjunction", "kind": "word_class", "words": ["conjunction"],
         "attrs": {"list": "and but or so because if when",
                   "does": "glues two thoughts together"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "question_word", "kind": "word_class", "words": ["question word"],
         "attrs": {"list": "what where when who why how which whose",
                   "does": "opens an open question"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        # punctuation
        {"id": "punctuation", "kind": "word_class", "words": ["punctuation"],
         "attrs": {"period": "ends a statement", "question": "? ends a question",
                   "exclaim": "! ends a shout", "comma": ", pauses inside",
                   "apostrophe": "' marks possession or contraction"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        # sentence patterns
        {"id": "pattern_sv", "kind": "pattern", "words": ["subject verb"],
         "attrs": {"example": "she walks", "does": "actor then action"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "pattern_svo", "kind": "pattern", "words": ["subject verb object"],
         "attrs": {"example": "she walks the dog", "does": "actor, action, target"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        {"id": "pattern_svc", "kind": "pattern", "words": ["subject verb complement"],
         "attrs": {"example": "she is happy", "does": "actor, link, state"},
         "relations": [{"to": "sentence_grammar", "rel": "is-a"}]},
        # grammar-type family growth (statement..passive taught in grammar-1)
        {"id": "future_tense", "kind": "grammar_type", "words": ["future tense", "future"],
         "attrs": {"example": "she will walk", "does": "moves the action to what's coming"},
         "relations": [{"to": "grammar", "rel": "is-a"}, {"to": "past_tense", "rel": "pairs-with"}]},
        {"id": "present_continuous", "kind": "grammar_type", "words": ["present continuous"],
         "attrs": {"example": "she is walking", "does": "freezes the action while it happens"},
         "relations": [{"to": "grammar", "rel": "is-a"}]},
        {"id": "gerund", "kind": "grammar_type", "words": ["gerund"],
         "attrs": {"example": "walking is fun", "does": "turns a verb into a thing"},
         "relations": [{"to": "grammar", "rel": "is-a"}]},
    ]


# ============================ WRITERS ==========================================
def _pack(domain, concepts):
    return {"domain": domain, "concepts": concepts}


def build_taxonomy1():
    cs = list(SPINE)
    cs.append(cat("idea", ["idea"], "a thought or concept that lives in minds", "entity"))
    for child, parent in FAMILY_LINKS + LIVING_LINKS:
        cs.append(cat(child, [child.replace("_", " ")], None, parent))
    cs += entity_concepts(ANIMALS)
    return _pack("the living world", cs)


def build_taxonomy2():
    cs = list(MADE_SPINE)
    cs += entity_concepts(MADE)
    return _pack("the made world", cs)


def build_verbs():
    cs = [{"id": "verb", "kind": "category", "words": ["verb", "verbs"],
           "attrs": {"def": "a word for an action or a state"}},
          {"id": "verb_x", "kind": "noun_form", "words": ["verb"],
           "attrs": {"plural": "verbs"}}]
    cs += verb_concepts()
    return _pack("verbs", cs)


def build_adj():
    cs = [{"id": "adjective", "kind": "category", "words": ["adjective", "adjectives"],
           "attrs": {"def": "a word that describes a thing"}}]
    cs += adj_concepts()
    return _pack("adjectives", cs)


def build_nouns():
    cs = [{"id": "noun", "kind": "category", "words": ["noun", "nouns"],
           "attrs": {"def": "a word for a thing, person or place"}}]
    cs += noun_concepts()
    return _pack("everyday nouns", cs)


def build_sent_grammar():
    return _pack("sentence grammar", sent_grammar_concepts())


def main():
    packs = [
        ("taxonomy-1.json", build_taxonomy1()),
        ("taxonomy-2.json", build_taxonomy2()),
        ("vocab-verbs.json", build_verbs()),
        ("vocab-adj.json", build_adj()),
        ("vocab-nouns.json", build_nouns()),
        ("sent-grammar.json", build_sent_grammar()),
    ]
    os.makedirs(CURR, exist_ok=True)
    for fn, pack in packs:
        path = os.path.join(CURR, fn)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        print("%-22s %4d concepts" % (fn, len(pack["concepts"])))


if __name__ == "__main__":
    main()
