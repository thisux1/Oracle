---
title: "Cards"
pageid: 1235
categories: [Uncategorized]
source: "https://epic-rpg.fandom.com/wiki/Cards"
related_pages: [None]
---

# Cards

1. #  Cards Overview 
Players can use the <code>rpg card hand</code> command to play a game of poker against the EPIC NPC.  It is possible to increase the rewards that you get from this command by collecting and crafting cards.

1. #  Card Drops 
Players will encounter card drops throughout their normal play.  There is one card per hunt monster, one card per adventure monster, one card per working command reward (i.e. coin from <code>rpg mine</code>, apples from <code>rpg greenhouse</code>).  Each drop has a specific rarity ranging from the following list:

- COMMON,
- UNCOMMON,
- RARE,
- EPIC,
- OMEGA,
- GODLY,
- VOID,
- ETERNAL.

In general, higher level cards will drop from hunt/adv monsters in higher areas, rarer working command results, etc.  Card drop chances are the same for all players (as of the cards update part 2, they do not scale on any player attribute including time travels), but they do differ based on the individual card drop.

You can track the card drops that you are missing with <code>rpg cards</code> and optionally include a page number to skip to that page.

Cards can be gotten from the following sources: 

- Hunt monsters
- Adventure monsters
- Working commands (one per working command drop)
- Performing alchemy (one per potion)
- Obtaining basic pets during pet approach events (one each for cat, dog, dragon)
- Opening lootboxes (one cards for each type of lootbox, including godly)

Drop rate for lootboxes scales with the number of lootboxes opened.
Cards show up in your inventory after they are acquired, and will remain until you use rpg card slots on them.  They are not lost upon time travelling.


- Note: Card drop rates cannot be increased by any potions, nor time travels.*

1. # Card Slots
Once you have three cards of a given rarity, you can use the <code>rpg card slots</code> command to combine them into a playing card.  For example, if you have at least 3 **uncommon** cards, use <code>rpg card slots uncommon</code> to craft a new uncommon poker card. 

If this playing card is in your final hand at the end of a game of <code>rpg card hand</code>, then you will get a bonus multiplier on the number of items that are dropped.  Additionally, higher rank cards will also net higher rewards multiplier (so a pair of tens will give a bigger bonus than a pair of twos); aces are considered the highest card.

View your poker cards with <code>rpg card deck</code>; the highlighted cards are those that you have acquired.

When using slots to craft cards, common cards are more likely to provide you with a low rank card (2,3,4) while higher ranking cards such as GODLY and ETERNAL are more likely to provide face cards and aces.

1. # Card Hand
Card hand has a 1d cooldown. It is a video poker game. You always play with a full deck of 52 playing cards. Cards that you don't own can be used, however each card you own in the final hand will increase the reward payout by 17% of the base rewards.

    - How to play:**  

- You start with 2 cards and play 3 rounds.
- Each round you can either select a card or you can pass.
- Selecting a card will discard that card and replace it with a random other card.
- Discarded cards can not appear again in the same game.
- Passing will keep all the cards you currently have.
- Regardless of your action you will get a new extra card.
- The game ends once you have 5 cards.
- Check <code>Winning hands</code> for all win conditions.

1. # Winning hands combination / expected rewards
| Hand | Cards | Base rewards |
| --- | --- | --- |
| Ace Extravaganza | Four Aces and a Joker | 10 time capsules |
| Royal Hearted Flush | 10-J-Q-K-A, all hearts | 3 time capsules |
| Royal Flush | 10-J-Q-K-A, all same suit (except hearts) | 1 time capsule |
| Ace Gala | Four Aces plus any fifth card | 1 time capsule |
| Straight Flush | Five sequential cards (except 10-J-Q-K-A), all same suit | 450 time cookies |
| Four of a Kind | Four of the same rank (except Aces) plus any fifth card | 250 time cookies |
| Full House | Three of the same rank plus a different pair | 160 time cookies |
| Game of Kings | Pair of Kings and pair of Queens plus any fifth different card | 140 time cookies |
| Flush | Any five non-sequential cards of the same suit | 120 time cookies |
| Unbreakable Fortress | Ace-2-3-4-5 of at least two suits | 90 time cookies |
| Straight | Five sequential cards (except A-2-3-4-5) of at least two suits | 70 time cookies |
| Three of a Kind | Three cards of the same rank plus two other non-matching cards | 35 time cookies |
| Two Pairs | Two different rank pairs (except Kings and Queens) and any other non-matching fifth card | 25 time cookies |
| Pair | Any two matching rank cards plus three other non-matching cards | 10 time cookies |
| Random Cards | Five different, non-sequential rank cards of at least two suits | 10 arena cookies |
| Timeout | You timed out | 5 arena cookies |


Hands that require matching ranks will award bonuses based on the rank of the cards. If two different sets of ranks are required (Two Pair, Full House), the increase is adjusted.

| Rank | % bonus | Rank | % bonus | Rank | % bonus |
| --- | --- | --- | --- | --- | --- |
| Ace | 70% | 9 | 45% | 4 | 20% |
| King | 65% | 8 | 40% | 3 | 15% |
| Queen | 60% | 7 | 35% | 2 | 10% |
| Jack | 55% | 6 | 30% |  |  |
| 10 | 50% | 5 | 25% |  |  |


Reward calculation: Base amount * (0.15 + 0.17 * cards owned in hand) * (1 + Rank bonus) (if applicable)
For example, two pair (queens and sevens) with three cards owned would be:
- Base amount * (0.15 + 0.17 * 3) * (1 + (0.60 + 0.35) / 2)
- Base amount * (0.66) * (1.475) = 97.35% of Base amount
Full House is an exception - again using queens and sevens, with 777QQ:
- Base amount * (0.15 + 0.17 * 3) * (1 + (0.60 + 0.35 * 2) / 3)
- Base amount * (0.66) * (1.433...) = 94.6% of Base amount

1. # Round cards

Round card  is a consumable item that can be used to receive the following boosts for **5** (**10 with the pocket watch artifact) minutes**:  

- -90% cooldown reduction
- +350% chance to drop lootboxes
- +350% chance to drop monster items
- +500% working items
- +200% chance to get better items in working commands
- Auto healing
- While its boost is activated, a player cannot use <code>dungeon</code>, <code>horse</code> or <code>cards</code>.
Additionally, you can use 125 commands (250 if you have the pocket watch artifact) in one go using a round card if you own 3 or more of them at the time of usage. 
    
 
 
 
It is, however, preferred to not use round cards without the pocket watch artifact.