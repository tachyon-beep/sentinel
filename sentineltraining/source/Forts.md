# Magic Gem Inventory

Your gem inventory’s contents are displayed in the national summary, and you can go to the gem inventory screen by clicking on any of the gem icons. The current monthly gem income is show in parenthesis after each gem type.

# Forts

Forts are structures which exist on the map and can be upgraded. They serve as:
- Collection points for resources
- Supply depots for distribution to surrounding provinces
- Shelter for troops in the event of a siege

Each fortress type has different attributes.

## Fortress Types

The numbers for "Build" indicate gold/months required. Because each level of fort must be built on the previous one, the months listed are for that specific stage only. 

For example:
- It would take 1000 gold and five months to build a palisade
- Then another 600 gold and three months to upgrade it to a fortress

The attributes don't stack, so the admin, recruitment, supply, and wall integrity of the previous fort are replaced by the new one.

### Era and Fort Availability

The era (Early, Middle, or Late) of the game dictates what fort levels are available to most nations:

- Early Age: fortress
- Middle Age: castle
- Late Age: citadel

Some nations (like Yomi) can only build primitive forts, while others (like EA Ermor) can build advanced forts compared to the standard of a particular era. The Nation Overview screen will inform you if the nation you are viewing has primitive or advanced forts.

### Masons

Some nations, such as Marignon and Ulm in the middle era, have masons who are able to construct forts one level higher than normal. This is not specifically a nation trait, but simply a trait on a particular commander that happens to be available to that nation at that time. A commander with the mason trait can be used to construct higher level forts.

The grand citadel is only available to those nations who can construct a citadel and also have a mason. It has the same icon as the citadel.

## Fort Attributes

### Admin

The admin value of a fort determines:
1. The percentage of resources from neighboring provinces that the fortress can collect
2. Supply propagation into nearby provinces

The formula for supply propagation is: `(Administration * 6) / (Distance + 1)`

For example, a fortress with admin 50 contributes 150 supply to adjacent provinces. Four provinces is the maximum distance for this supply propagation.

Administration also increases the income of a province by `Admin / 2%`. Thus, a fort with an Admin value of 30 would increase the income by 15% of any province in which it is built.

The admin value also propagates supplies to nearby provinces:

| Distance | Supply |
|----------|--------|
| 0        | 400%   |
| 1        | 200%   |
| 2        | 133%   |
| 3        | 100%   |
| 4        | 80%    |

### Defense

The defense value of a fort represents the number of points of damage that must be done to a fort by an enemy siege before it can be attacked. Each turn, a comparison is made between the strength of the sieging and besieged forces at a fortress. The difference between these forces determines the amount of damage done to the fortress' defense value.

### Supply

The supply value of a fortress determines only how many units can be supplied inside that fortress in the event of a siege. It does not affect the distribution of supply to surrounding provinces. 

Each turn a fortress is under siege, its supply value is divided by the length of the siege to determine the supply points available on that turn to the besieged units. For example, on the fifth turn of a siege of a fortress with a supply value of 100, the fortress provides besieged units with 20 supply.

## Fort Types and Their Attributes

| Name          | Build Cost | Build Time | Admin | Com. Points | Rec. Points | Supply Storage | Wall Integrity |
|---------------|------------|------------|-------|-------------|-------------|----------------|----------------|
| Palisades     | 1000       | 5          | 15    | +0          | +50%        | 150            | 200            |
| Fortress      | 600        | 3          | 30    | +1          | +75%        | 750            | 500            |
| Castle        | 600        | 3          | 45    | +1          | +100%       | 2500           | 1000           |
| Citadel       | 600        | 3          | 60    | +2          | +125%       | 7500           | 1500           |
| Grand Citadel | 1000       | 5          | 70    | +2          | +150%       | 10000          | 2000           |

## Castle Guards and Wall Defenders

Forts also have defense (termed Castle Guards and Wall Defenders) that will help defend the fort when it is being stormed. The Wall Defenders will be stationed on the walls and the Castle Guards will start behind the gate of the castle. These units will be replenished for each fight, just like normal province defence.

Castle Guards and Wall Defenders contribute to the repair strength of the defending army.

Wall Defenders also have the following attributes:

- Never run out of ammunition
- Can be attacked from the stairs inside the walls, or by Flying or Ethereal units (or missiles)
- 20% increased missile range
- Some protection from missiles. The wall has the same defense as a tower shield, but it has a Protection value of 30. The defenders use the best of their own shield or the wall defense.

The number of Castle Guards and Wall Defenders depends on the fort level.

## How Forts Collect Resources

The calculations for provincial resources can seem confusing. The most important thing to remember is that a province's resource pool only consists of half of that province's potential resource production as long as it has no fort. A province will only gain the benefit of its full production when that province has a fort.

Furthermore, once a province has a fort, the fort uses its Admin value to draw resources from adjacent provinces, within certain restrictions:

- A land fort cannot draw resources from an adjacent sea province and vice versa
- Forts cannot draw resources from adjacent provinces that also contain forts
- No fort can draw resources from an adjacent enemy province

[The document continues with detailed examples of resource collection calculations]

# Temples

Temples are the second of the three buildings you can construct in Dominions 6. Temples help you spread your dominion, either by directly inducing dominion spread [Exception: Mictlan, Early and Late Eras] or by providing a location for blood sacrifices (which are only available to certain nations – see the Dominion chapter). Temples also give priests a bonus when preaching.

Key points about temples:
- Can only be built in a friendly province
- If an enemy takes control of a province with another nation's temple, the temple is immediately razed
- Only one temple can exist in a province at a time
- Cost 600 gold to build, with some exceptions:
  - Man and Marverni only pay half this cost
  - Pangeaea pays half in a forest province
  - Late age Gath pays double everywhere

# Laboratories

Laboratories (or labs) are the last building type available. They serve as:
- Magic gem collection points
- Centers of research

Labs allow:
- Mages in that province to perform the Research order
- Transfer of gems from the national inventory
- Casting of ritual spells (only in a province with a laboratory)

Labs cost 600 gold to build, with some exceptions:
- Some nations can build cheaper labs (e.g., Arcoscephale)
- Pangeaea pays half in forest provinces (just like their temples)

# Magic Sites

Magic sites are locations within a province that possess some special attribute, like:
- Magic gem production
- Unique unit recruitment
- Other benefits

Key points about magic sites:
- A province may have multiple magic sites
- Not all may be visible at once
- More likely to be found in certain terrains (forests, wastes, deep seas)
- Less likely in other terrains (plains, farmlands)
- Must be discovered by searching
- Four levels of difficulty for discovery
- Mages must have skill in the magic path of the site equal to the difficulty level to find it
- Some sites allow certain types of units to enter them for benefits
- Sites which permit recruitment of national units only grant this ability to that nation
- Some sites may have additional requirements before becoming useful
- Not all magic sites have beneficial effects; some may cause unrest or other ill effects

# Province Defense

Province defense (PD) is a way of protecting a province without actually stationing an army there.

Key points about province defense:
- First level is free
- Subsequent levels cost gold equal to the new defense level
- Maximum level is 100
- Provides commanders and troops, with more at higher levels
- Every 10 points reduce unrest by 1 point per turn
- Starting at level 15, has a chance to detect stealthy units
- Province must have sufficient population to support PD (10 points of population per 1 point of PD)
- Cannot be reduced once built, except by capture or relinquishment in disciple games

# Unrest

Unrest represents people being unhappy with the ruler of the province.

Causes of unrest:
- Difference between controlling nation and dominating nation
- Blood hunting
- Enemy spies and bards
- Random events (e.g., ill omens)

Effects of unrest:
- Reduces income and resource generation
- At 100 or greater, prevents recruitment of new units

# Mercenaries

Mercenaries are units willing to fight for gold.

Key points about mercenaries:
- Hired for three-month periods
- Previous employer's bid counts double when contract runs out (for that turn only)
- Some nations get discounts on certain mercenary bands
- Some nations (e.g., Ermor - Ashen Empire) must pay more for most bands

# Scouting and Scrying

Various methods of gathering information about provinces:

1. Scout in province
2. Priest in province
3. Spy in province
4. Dominion in province
5. Scrying a province
6. Owning a province

Each method reveals different levels and types of information.

# AI Opponents

When starting a new game, you can choose the number and level of AI-controlled opponents.

AI levels and their resource bonuses:
- Easy AI: -30%
- Normal AI: 0
- Difficult AI: +30%
- Mighty AI: +60%
- Master AI: +100%
- Impossible AI: +150%

The bonus applies to money, resources, recruitment points, and magic, but not to commander recruitment rate or holy points.

AI players also get an information bonus, knowing which countries are owned by which players without needing scouts everywhere.