---
title: "Pets"
pageid: 371
categories: [Game_info, Mechanics]
source: "https://epic-rpg.fandom.com/wiki/Pets"
related_pages: [Anniversary, Christmas, Easter, Halloween, Horse Festival, Special Events, Valentine]
---

# Pets

Still feeling lonely despite there being four-player dungeon parties and guilds? Do you feel as if there is just something missing? As if there is a place in your heart that no amount of gold, materials, or mob drops could ever fill? Well, look no further friends because we now have the answer to your problem! Introducing: pets! Now you can have a cute little following of creatures that will accompany you and help you along your journey, making your rpg life easier!

    - Note**: The pet feature is only limited to players who have **time traveled 2 or more times (TT2+) **as well as for those who received a pet through other means [see next section]. Otherwise, you cannot receive pets.


1. # **How Do I Obtain Pets?**
Currently, there are three common types of pets you may encounter: Dogs, Cats and Dragons. **Please note that common pet types are purely aesthetic, only Special Pets (Ver: Pets#Special Pets) will provide extra benefits and buffs!** The max amount of pets a player can have is **five plus one for every time travel** the player has done.

As stated previously, there are multiple ways of receiving a pet! The main way is through the /**training** command, where you will have a chance of encountering one of the  three types of pets. There is a 4% chance of encountering one, but it increases to 10% if you have a Tier IX and 20% chance if you have a Tier X horse.

When encountering a pet, the information box will inform the player on the type and the tier of the pet. The box will also show the pets happiness and hunger levels, which the player will need to pay attention to. Increasing their chances of capturing the pet depends on these values and are affected by using the following inputs:
| Input | Description |
| --- | --- |
| Pat | Increases their happiness level (8-12) |
| Feed | Decreases their hunger level (18-22) |

Players will create a combination of these two inputs with a **max of six inputs** they are permitted to use. The less inputs used, however, the higher the chance that the pet will have a skill when captured.

In addition, pets can also be received from **giveaways hosted by the developer** or it may be offered as a prize for completing a challenge during a **seasonal event**. Another way to obtain pets is placing top 3 in Tier IX or top 1-3 in Tier X horse Race. Getting the pet prize in the Tier IX race can be from Tier 1-3, and The pet prize you get in Tier X race can be from Tier 1-5 with normie skill. **These are the only three ways for a player with less than 2 Time Travel to obtain pets.**

    - Pets are not tradeable!**
1. # **Commands**

1. ## **Adventure**
Command: **/pets adventure [ find / learn / drill ] [ ID ] [ ID ]** 

Your pets will help assist you in the little ways that they can: fetching items for you, digging up some coins, and improving themselves for your betterment! Players can issue a command for them every four hours. **You can only send one pet at a time unless a pet has an EPIC skill.** [See the Skills (Ver: Pets#Skills) section below for more details.]

Players can find the pet's ID in "/pet." Note: Pet ID's may change around after a pet fusion.
| Adventure Type | Description |
| --- | --- |
| Find | Pet will be more likely to find items |
| Learn* | Pet will be more likely to advance one skill |
| Drill | Pet will be more likely to find coins |

- Learn, when successful, will level up only **one** of the pet's skill(s). It will **not** grant a new skill.

Note: All adventure types are not guaranteed to find/improve like their description states. If the adventure "fails" as in it does not yield the targeted result, it will then randomly be the result of one of the other two.

Ex) /pets adventure learn a → pet does not improve a skill → pet brings back coins or items instead

Pet adventure rewards can be claimed using the command **/pets claim**, which will return the rewards from any pet that has completed an adventure.

To cancel a pet adventure, use the command **/pets adventure cancel** **[ID]** to bring back a pet sent out by mistake. Does not work on pets with the time traveler skill.

1. ## **Pet Tournament**
Command: **/pets tournament [ID]**

Players can send their pets to join the pet tournament, a scheduled event every 12 hours in which the higher the pet score the more likely the pet is to win and advance a tier. Pet tournaments are divided by tier totaling 10 categories and only one winner will be chosen per category. 

1. # **Pets: Tiers and Fusion**
1. ## **Tiers**
Pets, similar to your horse companion, also have a tier system that range from Tier I to Tier XXV and that will also grant a number of bonuses. These bonuses are the following:
- How many items the pet can get in a pet adventure
- The chance to increase the rank of a skill in a pet adventure
- The chance to preserve the skills in a pet fusion
1. # **Skills**
In addition to bonuses, pets may also hold skills that will boost their proficiency of their adventures and fusion results. There are 10 skills in total (excluding normie) and pets are able to have all ten skills.
| Skill | Description |
| --- | --- |
| Normie | No boost, absolutely nothing. Still cute though. |
| Fast | Requires less time to come back from an adventure. |
| Happy | Has a higher chance to get a better tier pet when used in pet fusion. |
| Clever | Higher chance to increase the rank of its skills in pet adventure. |
| Digger | Find more coins in pet adventure. Keep in mind that the skill name is deceiving as Drill is the action used to find coins. |
| Lucky | Find better item tiers in an adventure. |
| Time Traveler | Has a chance to come back from an adventure instantly. |
| EPIC ^[1][3] | If this pet is sent to an adventure, another one can be sent too.* |
| ASCENDED **^[2]** | Has chance to find a new pet in an adventure. |
| PERFECT **^[5]** | Has a chance to find multiple pets in an adventure |
| FIGHTER **[6]** | Has a chance to deal extra damage in dungeons, as well giving a chance to receive 1-3 dragon essence. Obtained upon reaching Tier X. |
| MASTER | Can bring higher tier pets if ascended. Obtained upon reaching Tier XV. |

^[1] **WARNING**: Must send this pet out **first**, otherwise you will not be able to send it out once a non-epic pet is sent out. 

^[2] The **ASCENDED** skill is different from the rest: it can only be obtained with <code>pets ascend</code>, cannot be advanced in an adventure and it cannot be lost in a fusion.

^[3]  Now you can send 2 or more pets at a time, with the updated command **/pets adventure [ find / learn / drill ] [ ID ] [ ID ]** (e.g. /pets adventure learn a b). You still need one pet to have EPIC skill.

^[4]  Each rank decreases the time it takes to come back from an adventure by 9 minutes and 36 seconds.

Each skill will have a rank, with F being the lowest and SS+ being the highest. Skill rank determines how good the skill is as well as how likely the skill will stay after a pet fusion. Each rank will be harder to get than the previous one.

^[5] This skill is an upgrade to the ASCENDED skill, it can only be obtained through fusing two ASCENDED SS+ skilled pets and then you will receive the PERFECT skill

[6] The chance to get dragon essence can be calculated with the following formula: 0.25 + 0.075 * tier (tier being 0 for rank F and 8 for rank SS+). So, 0.25 + 0.075 * 0 at rank F = 0.25 or 25% (chance to get 1 essence). 0.25 / 2 + 0.075 / 2 * 0 at rank F = 0.125 or 12.5% (chance to get 2 essence).                    0.25 / 3 + 0.075 / 3 * 0 at rank F = 0.08333... or ~8.3% (chance to get 3 essence).
1. # **Special Pets**
Each special pet has their own special skills that are unobtainable by others. These give extra boosts, making them overall better than normal pets.

1. ## Golden Bunny 
- Event: Easter
- Obtained from the Easter Event Challenge: Collect 10 golden eggs until the end of the event to receive a special Easter Lootbox.
- Special Skill **Faster**: Doubles the time reduced by the fast skill.

1. ## Hamster 
- Event: Anniversary, Compensation event #1 (Ver: Special Events#Compensation%20event%20.231), Celebration (Ver: Special Events#Celebration%20Event) and 500k servers (Ver: Special Events#500k%20servers)
- Special Skill **BOOSTER**: all pets have a high chance to advance skills twice in an adventure
- Note that this is a passive skill, meaning it is not required to send Hamster on an adventure to activate its skill.

1. ## Pumpkin Bat 

- Event: Halloween
- Obtained by defeating The Pumpkin Bat Event Boss, after collecting crafting and summoning a Spooky Scroll.
- Special Skill **Monster hunter**: It can find monster drops in an adventure.

1. ## Snowball

- Event: Christmas
- Obtained on Christmas for those who completed their Christmas tree.
- Special Skill **Gifter**: Has a chance to find lootboxes in an adventure.

1. ## Snowman 

- Event: Christmas
- Obtained by using an EPIC snowball
- Special Skill **Gifter**: Has better chance of finding higher tier of lootboxes in an adventure.

1. ## Penguin  

- Event: Christmas
- Obtained from high tier presents
- Special Skill  Antartician: Guarantees to bring back EPIC fish upon finding fish

1. ## Pink Fish 

- Event: Valentine
- Obtained from the Love Quest
- Special Skill **Fisherfish**: Gets x3 amount of fish from an adventure.

1. ## EPIC Panda

- An exclusive pet given to 𝒫𝟦𝓃𝒹𝒶#7896 for being the 1st person to achieve **100 time travels!**
- Special Skill **Competitive**: Adds one more pet score point.

1. ## Pony Pet 

- Event: Horse Festival
- Obtained from the Horse Festival Quest
- Special Skill **Farmer:** It can find seeds and special seeds in an adventure.

1. ## VOIDog 

- Obtained from dungeons 16 to 20. Higher area increases chance to find one, having more than one of this pet decreases chance to find one.
- Special skill  **RESETTER:** It is an upgraded version of the Time Traveler skill, being able to affect every single pet.

1. ##  Worker  

- Obtained as a crossover reward from Idle Farm. Received after reaching 25 achievements and using the **idle crossrewards** command.
- Special skill **LEADER**: all pets find 30% more items on an adventure. 
- Note that this is a passive skill, meaning it is not required to send Worker on an adventure to activate its skill.

1. ## EPIC Raven 

- An exclusive pet given to myrie929 for being the 1st person to achieve **1000 time travels!**
- Special Skill **Competetive:** Adds one more pet score point.

1. # **Fusion** 
Command: **/pets fusion [ IDs ]**

Players are able to combine their pets to receive a new one that has a chance of being better than the parent pets. Pet fusion is also a way for normie pets to have a chance of receiving a random skill, and as players can only obtain Tier 1-3 from training, pet fusion is therefore a must for obtaining Tier 4+ as well.

Pet fusion requires at least two pets and as long as there are at least two, players can feel free to fuse as many pets at once as they like. Do keep in mind that while more pets increases the chance to get a higher tiered pet, too high of a tier difference is not worth it.

Here are some things to note when fusing: 
- If the resulting pet does not tier up, it will be at least the tier of the higher tiered parent i.e. Tier 1 + Tier 2 = Tier 2 or 3
- Inheriting a skill is not guaranteed and is highly recommended that you take the time to rank up your skills before fusing.
- Pet type will be randomly selected from the pets used for the fusion. The only exception to this is event pets which will always be the resulting pet type.
- Pets with different special skills cannot be fused together.
- Chance to get a higher tier pet with fusion can be increased with Time Travel boost and Happy skill.

Here is a chart for recommended fusions for tier up personalized for your time travel:<gallery>
File:Pet-chart.png
</gallery>**Note**: Only one unique event pet can be fused in a single fusion

Additionally, if the player has a XV tier pet, the command **pets fusion automatic** will be available. This command will fuse all the pets without skills that are not of a special type.

1. #  **Pet Score**
The pet score has a very simple formula:

> Pet Tier * (Pet Tier + (Skill Score * Skill Level multiplier))

- Pet Tier is the Tier as a number
- Skill Score is based on the skill
- Skill Level is a number based on the Skill Level

| Skill | Skill score |
| --- | --- |
| Fast | 2 |
| Happy | 4 |
| Clever | 6 |
| Digger | 8 |
| Lucky | 10 |
| Time Traveler | 12 |
| EPIC | 14 |
| ASCENDED | 504 |


| Skill level | Skill level multiplier |
| --- | --- |
| F | 1 |
| E | 2 |
| D | 3 |
| C | 4 |
| B | 5 |
| A | 6 |
| S | 7 |
| SS | 8 |
| SS+ | 9 |

Category:Game info
Category:Mechanics