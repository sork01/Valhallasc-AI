"""The mercenary offers a group-quest giver carries (server: world/mercs.rs). Each rents one fighter of a class for 250
gold, up to the number of players the quest wants; the last one ends every contract. Used by generate_crags.py and
generate_gloamfen.py so both givers read the same."""
COST = 250
CLASSES = ['warrior', 'mage', 'assassin', 'priest', 'hunter']
BLURB = {'warrior': 'holds the line', 'mage': 'casts from range', 'assassin': 'strikes fast',
         'priest': 'heals the party', 'hunter': 'shoots from range'}


def offers(open_=False):
    """`open_`: the Meeting Stone's offers, which need no quest (any party of up to five may rent fighters)."""
    hire = [dict(id='merc_' + c, label=f'Hire a {c.capitalize()} mercenary · {BLURB[c]}', cost=COST, merc=c, **(dict(open=True) if open_ else {}))
            for c in CLASSES]
    return hire + [dict(id='merc_dismiss', label='Send my mercenaries away', cost=0, merc='dismiss')]
