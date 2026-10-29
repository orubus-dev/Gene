#!/usr/bin/env python3
"""Teacher-side generator — the academy lesson packs.

Same channel as every curriculum pack: structured lessons digested
through observe/inherit, never answers written into the organism. Writes:

  curriculum/maths-1.json       quantities, units, the foundational
                                formulary (~36 equations), math laws
  curriculum/science-bio.json   cells, genes, organs, systems, processes
  curriculum/science-chem.json  elements, compounds, reactions, states
  curriculum/science-phys.json  forces, energy, waves, electricity
  curriculum/science-geo.json   continents, oceans, countries, rivers
  curriculum/brain-1.json       brain regions, chemicals, emotions,
                                cross-species scans (human + animals)

Line format for entity blocks:  word|parent|key:value|key:value|...
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CURR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "curriculum")


def cat(cid, words, definition, parent=None):
    c = {"id": cid, "kind": "category",
         "words": words if isinstance(words, list) else [words],
         "attrs": {"def": definition}}
    if parent:
        c["relations"] = [{"to": parent, "rel": "is-a"}]
    return c


def ents(block, kind="entity"):
    out = []
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        word = parts[0]
        parent = parts[1] if len(parts) > 1 and parts[1] else None
        attrs = {}
        for kv in parts[2:]:
            if ":" in kv:
                k, v = kv.split(":", 1)
                attrs[k.strip()] = v.strip()
        c = {"id": word.replace(" ", "_"), "kind": kind,
             "words": [word], "attrs": attrs}
        if parent:
            c["relations"] = [{"to": parent, "rel": "is-a"}]
        out.append(c)
    return out


def write(name, concepts):
    path = os.path.join(CURR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"concepts": concepts}, f, ensure_ascii=False, indent=1)
    print("%-24s %d concepts" % (name, len(concepts)))


# ================================ MATHS =======================================
def build_maths():
    cs = [
        cat("quantity", ["quantity", "quantities"],
            "something that can be measured and counted", "entity"),
        cat("equation", ["equation", "equations", "formula"],
            "a rule that says two expressions are equal", "idea"),
        cat("unit", ["unit", "units"],
            "a standard amount used to measure a quantity", "entity"),
    ]
    cs += ents("""
speed|quantity|unit:metres per second|used_for:telling how fast something moves
velocity|quantity|unit:metres per second|role:speed with a direction
distance|quantity|unit:metre|used_for:measuring how far apart things are
time|quantity|unit:second|used_for:measuring how long things take
acceleration|quantity|unit:metre per second squared|role:how quickly speed changes
mass|quantity|unit:kilogram|role:how much matter something holds
weight|quantity|unit:newton|role:the pull of gravity on a mass
force|quantity|unit:newton|role:a push or a pull
momentum|quantity|unit:kilogram metre per second|role:mass on the move
energy|quantity|unit:joule|role:the ability to do work
work|quantity|unit:joule|role:force spent over a distance
power|quantity|unit:watt|role:how fast work gets done
pressure|quantity|unit:pascal|role:force spread over an area
area|quantity|unit:square metre|used_for:measuring a surface
volume|quantity|unit:cubic metre|used_for:measuring the space inside
density|quantity|unit:kilogram per cubic metre|role:how tightly packed the mass is
current|quantity|unit:ampere|role:electric charge on the move
voltage|quantity|unit:volt|role:the push behind a current
resistance|quantity|unit:ohm|role:how much a material fights the current
charge|quantity|unit:coulomb|role:the electric property of matter
temperature|quantity|unit:kelvin|role:how hot something is
frequency|quantity|unit:hertz|role:how often something repeats each second
wavelength|quantity|unit:metre|role:the span of one wave
height|quantity|unit:metre|used_for:measuring how tall something is
heat|quantity|unit:joule|role:energy moving from hot to cold
""", "quantity")
    cs += ents("""
metre|unit|symbol:m|used_for:measuring length
second|unit|symbol:s|used_for:measuring time
kilogram|unit|symbol:kg|used_for:measuring mass
newton|unit|symbol:N|used_for:measuring force
joule|unit|symbol:J|used_for:measuring energy
watt|unit|symbol:W|used_for:measuring power
pascal|unit|symbol:Pa|used_for:measuring pressure
ampere|unit|symbol:A|used_for:measuring current
volt|unit|symbol:V|used_for:measuring voltage
ohm|unit|symbol:Ω|used_for:measuring resistance
hertz|unit|symbol:Hz|used_for:measuring frequency
kelvin|unit|symbol:K|used_for:measuring temperature
""", "entity")
    # the foundational formulary — each equation is taught, never coded
    EQS = [
        ("eq_sum", "sum formula", "c=a+b", "arithmetic", "the total of two numbers"),
        ("eq_diff", "difference formula", "c=a-b", "arithmetic", "what is left after taking away"),
        ("eq_prod", "product formula", "c=a*b", "arithmetic", "one number taken many times"),
        ("eq_quot", "quotient formula", "c=a/b", "arithmetic", "one number shared by another"),
        ("eq_square", "square formula", "c=a^2", "algebra", "a number times itself"),
        ("eq_speed", "speed formula", "v=d/t", "kinematics", "speed from distance over time"),
        ("eq_kin1", "velocity formula", "v=u+a*t", "kinematics", "final velocity from starting speed"),
        ("eq_kin2", "distance formula", "s=u*t+0.5*a*t^2", "kinematics", "how far you travel while speeding up"),
        ("eq_accel", "acceleration formula", "a=(v-u)/t", "kinematics", "how fast the speed changed"),
        ("eq_newton", "force formula", "f=m*a", "mechanics", "newton's second law"),
        ("eq_weight", "weight formula", "w=m*g", "mechanics", "gravity's pull on a mass"),
        ("eq_momentum", "momentum formula", "p=m*v", "mechanics", "mass on the move"),
        ("eq_density", "density formula", "d=m/v", "matter", "mass squeezed into a volume"),
        ("eq_pressure", "pressure formula", "p=f/a", "mechanics", "force spread over an area"),
        ("eq_work", "work formula", "w=f*s", "mechanics", "force times the distance it moved"),
        ("eq_power", "power formula", "p=w/t", "mechanics", "work done each second"),
        ("eq_ke", "kinetic energy formula", "e=0.5*m*v^2", "energy", "the energy of motion"),
        ("eq_pe", "potential energy formula", "e=m*g*h", "energy", "the energy of height"),
        ("eq_ohm", "ohm's law", "v=i*r", "electricity", "voltage from current and resistance"),
        ("eq_epower", "electric power formula", "p=v*i", "electricity", "voltage times current"),
        ("eq_charge", "charge formula", "q=i*t", "electricity", "current flowing for a time"),
        ("eq_wave", "wave speed formula", "v=f*l", "waves", "frequency times wavelength"),
        ("eq_period", "period formula", "t=1/f", "waves", "one over the frequency"),
        ("eq_pythag", "pythagoras theorem", "c^2=a^2+b^2", "geometry", "the longest side of a right triangle"),
        ("eq_area_rect", "rectangle area formula", "a=l*w", "geometry", "length times width"),
        ("eq_area_tri", "triangle area formula", "a=0.5*b*h", "geometry", "half the base times the height"),
        ("eq_area_circ", "circle area formula", "a=pi*r^2", "geometry", "pi times the radius squared"),
        ("eq_circum", "circumference formula", "c=2*pi*r", "geometry", "around the circle"),
        ("eq_vol_box", "box volume formula", "v=l*w*h", "geometry", "length, width and height together"),
        ("eq_avg", "average formula", "m=(a+b)/2", "statistics", "the middle of two numbers"),
        ("eq_f2c", "fahrenheit formula", "f=9*c/5+32", "conversion", "celsius turned fahrenheit"),
        ("eq_einstein", "mass-energy formula", "e=m*c^2", "relativity", "mass is frozen energy"),
        ("eq_gas", "gas law", "n=p*v/(r*t)", "thermodynamics", "moles of gas from pressure and volume"),
        ("eq_grav", "gravity formula", "f=g*m*n/(d^2)", "mechanics", "the pull between two masses"),
        ("eq_hooke", "spring formula", "f=k*x", "mechanics", "a spring fights twice as hard"),
        ("eq_photon", "photon energy formula", "e=h*f", "quantum", "light's energy in its frequency"),
        ("eq_fall", "fall speed formula", "v=sqrt(2*g*h)", "kinematics", "how fast after falling from a height"),
    ]
    for eid, word, form, subject, gives in EQS:
        cs.append({"id": eid, "kind": "equation",
                   "words": [word, word.replace(" formula", " equation")],
                   "attrs": {"formula": form, "subject": subject, "gives": gives},
                   "relations": [{"to": "equation", "rel": "is-a"}]})
    cs += ents("""
commutative law||statement:a*b equals b*a — order does not matter in multiplication
associative law||statement:(a+b)+c equals a+(b+c) — grouping does not change a sum
distributive law||statement:a*(b+c) equals a*b+a*c — multiplication spreads over addition
identity law||statement:anything plus zero is itself; anything times one is itself
zero law||statement:anything times zero is zero
inverse law||statement:adding then subtracting the same number brings you back
pythagoras||statement:in a right triangle the square of the longest side equals the squares of the other two added
order of operations||statement:multiplication before addition, brackets first
""", "entity")
    write("maths-1.json", cs)


# ================================ BIOLOGY =====================================
def build_bio():
    cs = [
        cat("body_structure", ["body structure", "structure"],
            "a part of a living thing, from cells up to organs", "entity"),
        cat("cell_part", ["cell part", "organelle"],
            "a tiny working part inside a cell", "body_structure"),
        cat("tissue_cat", ["tissue"], "a family of cells doing one job", "body_structure"),
        cat("organ", ["organ", "organs"],
            "a body part built from tissues, doing a big job", "body_structure"),
        cat("life_system", ["body system", "system"],
            "a team of organs working on one life job", "body_structure"),
        cat("life_process", ["life process", "process"],
            "something living things do to stay alive", "idea"),
        cat("genetics_cat", ["genetics", "heredity"],
            "the study of how traits pass to offspring", "idea"),
    ]
    cs += ents("""
cell|body_structure|found_in:every living thing|role:the smallest unit of life
nucleus|cell_part|role:the cell's control room, holds the dna
mitochondria|cell_part|role:making energy for the cell|found_in:almost every cell
ribosome|cell_part|role:building proteins
chloroplast|cell_part|role:capturing sunlight for photosynthesis|found_in:plant cells
cell membrane|cell_part|role:the cell's gatekeeper, deciding what enters
cytoplasm|cell_part|role:the jelly inside a cell where work happens
vacuole|cell_part|role:storage tank of the cell|found_in:plant cells
cell wall|cell_part|role:the stiff outer skin|found_in:plant cells
dna|cell_part|used_for:storing the instructions for life|feature:the double helix
rna|cell_part|role:dna's working copy, carrying messages
gene|cell_part|role:a recipe for one trait|found_in:dna
chromosome|cell_part|role:a bundled thread of genes
protein|body_structure|role:the cell's building block and machine
enzyme|body_structure|role:a protein that speeds up chemistry
red blood cell|cell_part|role:carrying oxygen around the body|trait:round and red
white blood cell|cell_part|role:fighting germs and infection
neuron|cell_part|used_for:carrying electrical signals|found_in:the brain and nerves
platelet|cell_part|role:patching wounds with clots
stem cell|cell_part|role:a cell that can become any other cell
""", "entity")
    cs += ents("""
heart|organ|role:pumping blood around the body|trait:muscular and tireless
lungs|organ|used_for:breathing in oxygen and out carbon dioxide
brain|organ|role:the body's control centre and home of the mind
stomach|organ|role:breaking down food with acid
liver|organ|role:filtering the blood and making bile
kidney|organ|role:filtering waste into urine
skin|organ|role:wrapping the body and keeping germs out
eye|organ|used_for:seeing|feature:turns light into signals
ear|organ|used_for:hearing and balance
tongue|organ|used_for:tasting food
bones|organ|role:the body's frame and armour
muscle|tissue_cat|role:pulling on bones to move the body
blood|tissue_cat|role:the body's delivery service
nerve|tissue_cat|used_for:carrying signals at speed
""", "entity")
    cs += ents("""
circulatory system|life_system|role:moving blood, oxygen and food everywhere
respiratory system|life_system|role:breathing — oxygen in, carbon dioxide out
digestive system|life_system|role:breaking food into usable fuel
nervous system|life_system|role:sensing, deciding, commanding
skeletal system|life_system|role:support, protection and movement
muscular system|life_system|role:all the body's pulling
immune system|life_system|role:hunting germs and remembering enemies
endocrine system|life_system|role:hormones — the body's chemical mail
""", "entity")
    cs += ents("""
photosynthesis|life_process|effect:plants turn sunlight, water and carbon dioxide into food
respiration|life_process|effect:cells burn food with oxygen to release energy
digestion|life_process|effect:food gets broken down into fuel
growth|life_process|effect:living things get bigger using food
reproduction|life_process|effect:living things make new living things
evolution|life_process|effect:species change over generations
natural selection|life_process|effect:the fittest survive and breed, so their traits spread
adaptation|life_process|effect:species fit their habitat over time
metabolism|life_process|effect:all the chemistry that keeps a body running
homeostasis|life_process|effect:the body keeps its inside steady
germination|life_process|effect:a seed wakes and becomes a plant
pollination|life_process|effect:pollen moves so plants can make seeds
""", "entity")
    cs += ents("""
heredity|genetics_cat|role:passing traits from parents to young
trait|genetics_cat|role:a feature an organism carries, like fur colour
dominant|genetics_cat|role:a trait that shows even with one copy
recessive|genetics_cat|role:a trait that hides unless both copies agree
mutation|genetics_cat|effect:a random change in dna, sometimes new traits
genome|genetics_cat|role:the complete recipe book of an organism
clone|genetics_cat|role:an exact copy of one organism
punnett square|genetics_cat|used_for:predicting which traits the young can get
""", "entity")
    write("science-bio.json", cs)


# ================================ CHEMISTRY ===================================
def build_chem():
    cs = [
        cat("substance", ["substance", "matter"],
            "the stuff things are made of", "entity"),
        cat("element", ["element", "elements"],
            "a pure substance that cannot be split", "substance"),
        cat("metal", ["metal", "metals"],
            "a shiny element that conducts electricity", "element"),
        cat("nonmetal", ["nonmetal", "nonmetals"],
            "an element that is not a metal", "element"),
        cat("compound", ["compound", "compounds"],
            "a substance built from two or more elements", "substance"),
        cat("mixture_cat", ["mixture"],
            "two substances jumbled together but not bonded", "substance"),
        cat("state_cat", ["state of matter"],
            "the form a substance takes — solid, liquid, gas or plasma", "idea"),
        cat("atom_part", ["atom part"],
            "a piece inside an atom", "entity"),
        cat("reaction_cat", ["reaction", "chemical reaction"],
            "a change that turns substances into new substances", "idea"),
    ]
    ELS = [("hydrogen", "H", "1", "gas", "rocket fuel"), ("helium", "He", "2", "gas", "balloons"),
           ("lithium", "Li", "3", "solid", "batteries"), ("carbon", "C", "6", "solid", "all life"),
           ("nitrogen", "N", "7", "gas", "most of the air"), ("oxygen", "O", "8", "gas", "breathing"),
           ("fluorine", "F", "9", "gas", "toothpaste"), ("neon", "Ne", "10", "gas", "bright signs"),
           ("sodium", "Na", "11", "solid", "salt"), ("magnesium", "Mg", "12", "solid", "burning white"),
           ("aluminium", "Al", "13", "solid", "foil and cans"), ("silicon", "Si", "14", "solid", "computer chips"),
           ("phosphorus", "P", "15", "solid", "matches"), ("sulfur", "S", "16", "solid", "yellow powder"),
           ("chlorine", "Cl", "17", "gas", "pools"), ("argon", "Ar", "18", "gas", "light bulbs"),
           ("potassium", "K", "19", "solid", "bananas"), ("calcium", "Ca", "20", "solid", "bones"),
           ("titanium", "Ti", "22", "solid", "jet engines"), ("chromium", "Cr", "24", "solid", "shine on steel"),
           ("iron", "Fe", "26", "solid", "steel and blood"), ("nickel", "Ni", "28", "solid", "coins"),
           ("copper", "Cu", "29", "solid", "wires"), ("zinc", "Zn", "30", "solid", "coating steel"),
           ("silver", "Ag", "47", "solid", "the best conductor"), ("tin", "Sn", "50", "solid", "cans"),
           ("iodine", "I", "53", "solid", "antiseptic"), ("gold", "Au", "79", "solid", "never rusts"),
           ("mercury", "Hg", "80", "liquid", "old thermometers"), ("lead", "Pb", "82", "solid", "heavy shielding"),
           ("uranium", "U", "92", "solid", "nuclear fuel"), ("tungsten", "W", "74", "solid", "filaments")]
    for name, sym, num, state, used in ELS:
        kind = "metal" if name in ("lithium", "sodium", "magnesium", "aluminium",
                                   "potassium", "calcium", "titanium", "chromium",
                                   "iron", "nickel", "copper", "zinc", "silver",
                                   "tin", "gold", "mercury", "lead", "tungsten") \
            else "nonmetal"
        cs.append({"id": name, "kind": "element", "words": [name],
                   "attrs": {"symbol": sym, "number": num, "state": state,
                             "used_for": used},
                   "relations": [{"to": kind, "rel": "is-a"}]})
    cs += ents("""
water|compound|formula:h2o|found_in:rains rivers and you|used_for:drinking and every known life
carbon dioxide|compound|formula:co2|found_in:exhaled breath and fizzy drinks|effect:plants breathe it in
methane|compound|formula:ch4|found_in:natural gas|used_for:cooking and heating
ammonia|compound|formula:nh3|used_for:fertiliser and cleaning|trait:sharp smelling
salt|compound|formula:nacl|used_for:seasoning food|found_in:the sea
glucose|compound|formula:c6h12o6|role:sugar that fuels living things
ethanol|compound|formula:c2h5oh|found_in:drinks and fuel
rust|compound|formula:fe2o3|effect:slowly eats iron|trait:flaky and orange
baking soda|compound|formula:nahco3|used_for:baking and fizzing
vinegar|compound|formula:c2h4o2|used_for:cooking and cleaning|trait:sour
hydrogen peroxide|compound|formula:h2o2|used_for:cleaning wounds|effect:fizzes on germs
carbon monoxide|compound|formula:co|effect:a silent poison from bad burning
sulfuric acid|compound|formula:h2so4|used_for:car batteries|trait:very corrosive
ozone|compound|formula:o3|role:the sunburn shield high in the sky
""", "entity")
    cs += ents("""
bronze|mixture_cat|made_of:copper and tin|used_for:statues and old weapons
steel|mixture_cat|made_of:iron and carbon|used_for:buildings and tools
air|mixture_cat|made_of:nitrogen and oxygen and more|found_in:everywhere
saline|mixture_cat|made_of:salt and water|used_for:medical drips
""", "entity")
    cs += ents("""
solid|state_cat|trait:keeps its shape|effect:particles lock in place
liquid|state_cat|trait:flows and takes the container's shape
gas|state_cat|trait:spreads to fill any space
plasma|state_cat|trait:electrically charged gas, like lightning
melting|state_cat|effect:solid turns to liquid when heated
freezing|state_cat|effect:liquid turns to solid when cooled
evaporation|state_cat|effect:liquid turns to gas
condensation|state_cat|effect:gas turns to liquid when cooled
""", "entity")
    cs += ents("""
proton|atom_part|charge:positive|found_in:the nucleus
neutron|atom_part|charge:none|found_in:the nucleus
electron|atom_part|charge:negative|role:orbits the nucleus and makes bonds
atomic nucleus|atom_part|role:the heavy heart of an atom
""", "entity")
    RXNS = [
        ("water_formation", "hydrogen + oxygen", "water"),
        ("rusting", "iron + oxygen", "rust"),
        ("burning_carbon", "carbon + oxygen", "carbon dioxide"),
        ("salt_formation", "sodium + chlorine", "salt"),
        ("methane_burning", "methane + oxygen", "carbon dioxide"),
        ("ammonia_making", "nitrogen + hydrogen", "ammonia"),
    ]
    for rid, reacts, prod in RXNS:
        cs.append({"id": rid, "kind": "reaction", "words": [rid.replace("_", " ")],
                   "attrs": {"reactants": reacts, "product": prod},
                   "relations": [{"to": "reaction_cat", "rel": "is-a"}]})
    cs += ents("""
combustion|reaction_cat|effect:burning — fuel meets oxygen and releases energy|reactants:fuel + oxygen|product:heat and light
oxidation|reaction_cat|effect:oxygen joins a substance|reactants:element + oxygen|product:an oxide
neutralisation|reaction_cat|effect:acid and base cancel into salt and water|reactants:acid + base|product:salt and water
electrolysis|reaction_cat|effect:electric current splits a compound|reactants:compound + electricity|product:separate elements
photosynthesis reaction|reaction_cat|effect:plants make glucose from light|reactants:carbon dioxide + water|product:glucose and oxygen
""", "entity")
    write("science-chem.json", cs)


# ================================ PHYSICS =====================================
def build_phys():
    cs = [
        cat("physics_thing", ["physics thing"],
            "something physics studies — forces, energy, waves and fields", "entity"),
        cat("force_type", ["force type"], "a kind of push or pull", "physics_thing"),
        cat("energy_type", ["energy type"], "a form energy takes", "physics_thing"),
        cat("wave_type", ["wave type"], "a ripple that carries energy", "physics_thing"),
        cat("electric_thing", ["electric thing"],
            "something in the world of electricity and magnetism", "physics_thing"),
    ]
    cs += ents("""
gravity|force_type|effect:pulls everything toward everything, down toward earth's centre
friction|force_type|effect:slows surfaces sliding past each other|trait:a hidden brake
magnetism|force_type|effect:pulls iron and steers compasses
tension|force_type|role:the pull along a rope
buoyancy|force_type|effect:pushes floating things up
inertia|physics_thing|role:things keep doing what they're doing until forced
momentum conservation|physics_thing|statement:momentum never vanishes, only passes on
speed of light|physics_thing|role:the universe's speed limit — 300000 km per second
black hole|physics_thing|effect:gravity so strong not even light escapes
big bang|physics_thing|role:the start of everything, 13.8 billion years ago
""", "entity")
    cs += ents("""
kinetic energy|energy_type|role:the energy of motion
potential energy|energy_type|role:energy stored by position, like height
thermal energy|energy_type|role:the jiggle of particles — heat
chemical energy|energy_type|role:energy parked in bonds, like food and fuel
nuclear energy|energy_type|role:energy in the atom's heart
solar energy|energy_type|role:energy arriving from sunlight
sound energy|energy_type|role:energy riding through air as vibrations
light energy|energy_type|role:energy racing as light waves
conduction|physics_thing|effect:heat travels through touching matter
convection|physics_thing|effect:heat rides on moving fluids
radiation|physics_thing|effect:heat travels as waves, even through space
""", "energy_type")
    cs += ents("""
light|wave_type|trait:the fastest wave there is|effect:lets eyes see
sound|wave_type|trait:needs air or water to travel|effect:carries voices and music
echo|wave_type|effect:sound bounces back from a wall
reflection|wave_type|effect:light bounces off mirrors
refraction|wave_type|effect:light bends entering water or glass
diffraction|wave_type|effect:waves bend around corners
resonance|wave_type|effect:matching frequencies amplify a wave
doppler effect|wave_type|effect:moving sirens change pitch
""", "wave_type")
    cs += ents("""
electric current|electric_thing|role:charge flowing in a loop
circuit|electric_thing|role:the closed loop a current needs
battery|electric_thing|used_for:storing chemical energy as electric push
magnet|electric_thing|effect:attracts iron, has a north and south pole
electromagnet|electric_thing|role:a magnet switched on by current
static electricity|electric_thing|effect:charge builds up then jumps — a zap
lightning|electric_thing|effect:sky-sized static discharge
conductor|electric_thing|role:lets current pass easily, like copper
insulator|electric_thing|role:block current, like rubber
semiconductor|electric_thing|role:sometimes conducts — the heart of chips
 transformer|electric_thing|used_for:stepping voltage up or down
""", "electric_thing")
    write("science-phys.json", cs)


# ================================ GEOGRAPHY ===================================
def build_geo():
    cs = [
        cat("place_cat", ["place", "places"],
            "a location on earth or beyond", "entity"),
        cat("continent_cat", ["continent"],
            "one of earth's seven great land masses", "place_cat"),
        cat("ocean_cat", ["ocean"],
            "one of earth's five great waters", "place_cat"),
        cat("country", ["country", "countries"],
            "a nation with borders and a government", "place_cat"),
        cat("river", ["river", "rivers"],
            "a long flow of water crossing the land", "place_cat"),
        cat("mountain_cat", ["mountain"],
            "a towering height of rock", "place_cat"),
        cat("desert_cat", ["desert"],
            "a land so dry it barely rains", "place_cat"),
        cat("biome", ["biome"],
            "a big region with its own climate and life", "place_cat"),
    ]
    cs += ents("""
africa|continent|trait:the cradle of humankind|feature:home to the sahara and the nile
antarctica|continent|trait:the coldest, windiest continent|found_in:the south pole
asia|continent|trait:the biggest continent|feature:home to mount everest and china
australia|continent|trait:an island continent|feature:home of the kangaroo
europe|continent|trait:a peninsula of peninsulas|feature:home to the alps
north america|continent|feature:from alaska to panama|found_in:the western hemisphere
south america|continent|feature:home to the amazon rainforest|found_in:the southern hemisphere
pacific ocean|ocean|trait:the largest ocean on earth|found_in:between asia and the americas
atlantic ocean|ocean|trait:the second largest|found_in:between the americas and europe-africa
indian ocean|ocean|trait:the warmest ocean|found_in:south of asia
arctic ocean|ocean|trait:the smallest, coldest ocean|found_in:around the north pole
southern ocean|ocean|found_in:around antarctica
""", "entity")
    CS = [("canada", "ottawa", "north america", "english and french"),
          ("brazil", "brasilia", "south america", "portuguese"),
          ("egypt", "cairo", "africa", "arabic"),
          ("nigeria", "abuja", "africa", "english"),
          ("kenya", "nairobi", "africa", "swahili and english"),
          ("japan", "tokyo", "asia", "japanese"),
          ("china", "beijing", "asia", "mandarin"),
          ("india", "new delhi", "asia", "hindi and english"),
          ("russia", "moscow", "europe", "russian"),
          ("germany", "berlin", "europe", "german"),
          ("france", "paris", "europe", "french"),
          ("italy", "rome", "europe", "italian"),
          ("spain", "madrid", "europe", "spanish"),
          ("united kingdom", "london", "europe", "english"),
          ("united states", "washington dc", "north america", "english"),
          ("mexico", "mexico city", "north america", "spanish"),
          ("argentina", "buenos aires", "south america", "spanish"),
          ("australia_country", "canberra", "australia", "english"),
          ("south africa", "pretoria", "africa", "eleven official languages"),
          ("ethiopia", "addis ababa", "africa", "amharic")]
    for cid, cap, cont, lang in CS:
        nm = "australia (country)" if cid == "australia_country" else cid
        cs.append({"id": cid, "kind": "country", "words": [nm],
                   "attrs": {"capital": cap, "continent": cont, "language": lang},
                   "relations": [{"to": "country", "rel": "is-a"}]})
    cs += ents("""
nile|river|length:6650 km|flows:egypt and sudan|trait:the longest river
amazon river|river|length:6400 km|flows:peru and brazil|trait:carries the most water
yangtze|river|length:6300 km|flows:china
mississippi|river|length:3700 km|flows:the united states
danube|river|length:2850 km|flows:through ten countries in europe
congo river|river|length:4700 km|flows:the congo rainforest
volga|river|length:3530 km|flows:russia|trait:europe's longest
thames|river|length:346 km|flows:london
mount everest|mountain|height:8849 m|found_in:the himalayas|trait:the roof of the world
k2|mountain|height:8611 m|found_in:the karakoram
kilimanjaro|mountain|height:5895 m|found_in:tanzania|trait:a snowy giant near the equator
mount fuji|mountain|height:3776 m|found_in:japan
mont blanc|mountain|height:4808 m|found_in:the alps
denali|mountain|height:6190 m|found_in:alaska
sahara|desert|found_in:north africa|trait:the largest hot desert
gobi|desert|found_in:mongolia and china|trait:a cold desert
kalahari|desert|found_in:southern africa
atacama|desert|found_in:chile|trait:the driest place on earth
antarctic desert|desert|found_in:antarctica|trait:the largest desert of all
rainforest biome|biome|feature:wet, dense and bursting with species|found_in:the equator
savanna biome|biome|feature:grassland with scattered trees|found_in:africa
tundra biome|biome|feature:frozen ground and short summers|found_in:the far north
coral reef biome|biome|feature:underwater cities built by tiny animals|found_in:warm shallow seas
taiga biome|biome|feature:endless conifer forest|found_in:russia and canada
""", "entity")
    write("science-geo.json", cs)


# ================================ BRAIN =======================================
def build_brain():
    cs = [
        cat("brain_region", ["brain region", "region"],
            "a working district of the brain", "entity"),
        cat("neurotransmitter", ["neurotransmitter", "brain chemical"],
            "a chemical the brain uses to signal", "quantity"),
        cat("emotion_cat", ["emotion", "emotions", "feeling"],
            "a felt state of the mind", "idea"),
        cat("brain_scan", ["brain scan", "scan"],
            "a 3D map of a brain's regions", "entity"),
    ]
    cs += ents("""
prefrontal cortex|brain_region|role:plans, decides, holds the working thread|trait:the conductor
cortex|brain_region|role:the wrinkled thinking sheet where concepts live
motor cortex|brain_region|role:commands the body's movements
broca's area|brain_region|role:speech production — putting words out
wernicke's area|brain_region|role:language understanding — taking words in
visual cortex|brain_region|role:turning light into sight
auditory cortex|brain_region|role:turning vibrations into sound
hippocampus|brain_region|role:files new experiences into long-term memory
amygdala|brain_region|role:the alarm bell — fear and emotional coloring
hypothalamus|brain_region|role:runs hormones, hunger, thirst and temperature
thalamus|brain_region|role:the relay station for attention
basal ganglia|brain_region|role:habits and predicted rewards
cerebellum|brain_region|role:balance, timing and practiced moves
brainstem|brain_region|role:breathing and heartbeat — keeps the lights on
""", "entity")
    cs += ents("""
dopamine|neurotransmitter|role:reward and motivation|baseline:0.3
serotonin|neurotransmitter|role:mood stability and calm|baseline:0.45
norepinephrine|neurotransmitter|role:alertness and fight-or-flight|baseline:0.25
cortisol|neurotransmitter|role:stress signal|baseline:0.15
oxytocin|neurotransmitter|role:bonding and trust|baseline:0.25
acetylcholine|neurotransmitter|role:learning and attention|baseline:0.3
gaba|neurotransmitter|role:the brain's brake pedal|baseline:0.4
endorphin|neurotransmitter|role:eases pain after effort|baseline:0.2
glutamate|neurotransmitter|role:the gas pedal of plasticity|baseline:0.35
""", "entity")
    EMOS = [("joy", [0.85, 0.8, 0.2, 0.05, 0.4, 0.4, 0.35, 0.5, 0.4]),
            ("calm", [0.35, 0.7, 0.15, 0.08, 0.45, 0.25, 0.8, 0.4, 0.2]),
            ("fear", [0.2, 0.2, 0.9, 0.8, 0.1, 0.5, 0.15, 0.1, 0.6]),
            ("anger", [0.4, 0.15, 0.85, 0.7, 0.1, 0.4, 0.15, 0.3, 0.7]),
            ("sadness", [0.1, 0.15, 0.2, 0.5, 0.3, 0.2, 0.5, 0.1, 0.2]),
            ("surprise", [0.6, 0.4, 0.8, 0.3, 0.2, 0.6, 0.3, 0.2, 0.6]),
            ("excitement", [0.8, 0.6, 0.75, 0.2, 0.3, 0.7, 0.25, 0.35, 0.65]),
            ("affection", [0.55, 0.7, 0.2, 0.05, 0.9, 0.35, 0.55, 0.45, 0.3]),
            ("curiosity", [0.6, 0.5, 0.55, 0.1, 0.25, 0.85, 0.4, 0.25, 0.6]),
            ("frustration", [0.15, 0.2, 0.7, 0.65, 0.15, 0.5, 0.2, 0.15, 0.55])]
    CHEMS = ["dopamine", "serotonin", "norepinephrine", "cortisol", "oxytocin",
             "acetylcholine", "gaba", "endorphin", "glutamate"]
    for i, (name, sig) in enumerate(EMOS):
        attrs = {"ch_" + c: str(v) for c, v in zip(CHEMS, sig)}
        cs.append({"id": name, "kind": "emotion", "words": [name],
                   "attrs": attrs, "relations": [{"to": "emotion_cat", "rel": "is-a"}]})
    SCANS = [
        ("human_brain_scan", "1.0", "cortex:1.0;prefrontal:1.0;broca:1.0;"
         "wernicke:1.0;hippocampus:0.9;amygdala:0.8;cerebellum:0.9;"
         "hypothalamus:0.9;thalamus:1.0;basal_ganglia:0.9;visual:0.9;"
         "auditory:0.9;motor:0.9;brainstem:1.0",
         "the reference scan — symbolic thought and language"),
        ("mouse_brain_scan", "0.25", "cortex:0.6;hippocampus:1.0;amygdala:0.9;"
         "cerebellum:1.0;olfactory:1.0;brainstem:1.0;thalamus:0.8",
         "tiny but a memory and navigation champion"),
        ("octopus_brain_scan", "0.4", "cortex:0.9;visual:1.2;motor:1.1;"
         "basal_ganglia:0.7;brainstem:0.8",
         "half its neurons live in the arms — distributed problem solving"),
        ("crow_brain_scan", "0.3", "cortex:1.1;prefrontal:0.9;visual:1.1;"
         "motor:0.8;hippocampus:0.8;thalamus:0.9",
         "a bird that reasons with tools despite a pea-sized cortex"),
        ("dolphin_brain_scan", "0.45", "cortex:1.1;auditory:1.4;broca:0.5;"
         "wernicke:0.5;hippocampus:0.8;amygdala:0.9;cerebellum:1.0",
         "echolocation and social brains of the sea"),
    ]
    for sid, w, regs, note in SCANS:
        cs.append({"id": sid, "kind": "brain_scan", "words": [sid.replace("_", " ")],
                   "attrs": {"weight": w, "regions": regs, "feature": note},
                   "relations": [{"to": "brain_scan", "rel": "is-a"}]})
    cs += ents("""
human brain||role:86 billion neurons, the most stereotyped dreamer known|trait:folds itself for surface area
synapse||role:the gap where neurons talk in chemicals
neuroplasticity||effect:the brain rewires itself with practice — gene's whole life
""", "entity")
    write("brain-1.json", cs)


def main():
    build_maths()
    build_bio()
    build_chem()
    build_phys()
    build_geo()
    build_brain()


if __name__ == "__main__":
    main()
