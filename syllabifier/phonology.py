# coding=utf-8

import re

# Finnish phones --------------------------------------------------------------

# Finnish vowels
VOWELS = [u'i', u'e', u'A', u'y', u'O', u'a', u'u', u'o']
# ä is replaced by A
# ö is replaced by O


# Finnish diphthongs
DIPHTHONGS = [
    u'ai', u'ei', u'oi', u'Ai', u'Oi', u'au', u'eu', u'ou', u'ey', u'Ay',
    u'Oy', u'ui', u'yi', u'iu', u'iy', u'ie', u'uo', u'yO', u'oy']


# Finnish consonants
CONSONANTS = [
    u'b', u'c', u'd', u'f', u'g', u'h', u'j', u'k', u'l', u'm', u'n', u'p',
    u'q', u'r', u's', u't', u'v', u'x', u'z', u"'"]


# Finnish consonant clusters (see Karlsson 1985, #4)
CLUSTERS = [
    u'bl', u'br', u'dr', u'fl', u'fr', u'gl', u'gr', u'kl', u'kr', u'kv',
    u'pl', u'pr', u'cl', u'qv', u'schm']


# Phonotactic functions -------------------------------------------------------

def is_vowel(ch):
    return ch in VOWELS


def is_consonant(ch):
    # return ch in CONSONANTS
    return not is_vowel(ch)  # includes 'w' and other foreign characters


def is_coronal(ch):
    # return ch in [u's', u'z', u'd', u't', u'r', u'n', u'l']
    return ch in [u's', u't', u'r', u'n', u'l']  # Suomi et al. 2008


def is_sonorant(ch):
    return ch in [u'm', u'n', u'l', u'r']


def is_cluster(ch):
    return ch in CLUSTERS


def is_diphthong(chars):
    return chars in DIPHTHONGS


def is_long(chars):
    return chars == chars[0] * len(chars)


# Linguistic constraints ------------------------------------------------------

phonemic_inventory = [
    u'i', u'e', u'A', u'y', u'O', u'a', u'u', u'o', u' ', u'-',
    u'd', u'h', u'j', u'k', u'l', u'm', u'n', u'p', u'r', u's', u't', u'v',
]

word_final_inventory = [
    u'i', u'e', u'A', u'y', u'O', u'a', u'u', u'o',  # vowels
    u'l', u'n', u'r', u's', u't',  # coronal consonants
]

onsets_inventory = [
    u'pl', u'pr', u'tr', u'kl', u'kr', u'sp', u'st', u'sk', u'ps', u'ts',
    u'sn', u'dr', u'spr', u'str',
]

codas_inventory = [u'ps', u'ts', u'ks']


def is_foreign(segments):
    word = replace_umlauts(''.join(segments))

    # if the word ends in a non-coronal consonant (excluding /d/), it is likely
    # foreign
    if len(word) > 1 and not word[-1] in word_final_inventory:
        return True

    foreign_chars = set([c for c in word if c not in phonemic_inventory])

    # the letter 'g' indicates a foreign word unless it is preceded by an 'n',
    # in which case, their collective underlying form is /ŋ/, which does appear
    # in the Finnish phonemic inventory
    if set('g') == foreign_chars:
        g = word.index('g')
        return not g or word[g - 1] != 'n'

    return bool(foreign_chars)


# Vowel Harmony ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FRONT_VOWELS = [u'A', u'y', u'O']

BACK_VOWELS = [u'a', u'u', u'o']

NEUTRAL_VOWELS = [u'e', u'i']


def is_front(ch):
    return ch in FRONT_VOWELS


def is_back(ch):
    return ch in BACK_VOWELS


def is_neutral(ch):
    return ch in NEUTRAL_VOWELS

DEPTH = {
    'A': 'front',
    'y': 'front',
    'O': 'front',
    'a': 'back',
    'u': 'back',
    'o': 'back',
    }


def harmonic(word, foreign=False):
    # if foreign:
    #     return True

    # check if the vowels agree in front/back harmony
    vowels = filter(is_vowel, [ch for ch in word])
    vowels = filter(lambda x: not is_neutral(x), vowels)
    depths = map(lambda x: DEPTH[x], vowels)

    return len(set(depths)) < 2


# Sonority Sequencing ~~~~~~~~~~~~~~~~~~~~~~~~~~~

sonorities = {
    # sibilant /s/
    u's': 0,

    # obstruents
    u'p': 1,
    u'b': 1,
    u't': 1,
    u'd': 1,
    u'c': 1,  # TODO
    u'q': 1,  # TODO
    u'x': 1,  # TODO
    u'k': 1,
    u'g': 1,
    u"'": 1,
    u'f': 1,
    u'v': 1,
    u'z': 1,
    u'h': 1,

    # approximants
    u'l': 2,
    u'r': 2,
    u'j': 2,
    u'w': 2,  # TODO

    # nasals
    u'm': 3,
    u'n': 3,
    }


def sonseq(word, foreign=False):
    # check if the word has good sonority peaks
    def is_sloping(word, rising=True):
        slope = [sonorities.get(s, 0) for s in word]

        return slope == sorted(list(set(slope)), reverse=not rising)

    parts = re.split(r'([ieAyOauo]+)', word)
    onset, coda = parts[0], parts[-1]

    # if foreign:
    #     return is_sloping(onset) and is_sloping(coda, rising=False)

    #  simplex onset      Finnish complex onset
    if len(onset) <= 1 or onset in onsets_inventory:
        #      simplex coda    Finnish complex coda
        return len(coda) <= 1  # or coda in codas_inventory

    return False


# MinWord ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def min_word(word, _):
    # check if the segment contains more than one vowel
    return len(filter(is_vowel, word)) > 1


# *VVC ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def not_VVC(word, _):
    # check that the word is not of the form VVC
    if len(word) == 3:
        return not(
            is_vowel(word[0]) and
            is_vowel(word[1]) and
            is_consonant(word[2])
            )

    return True


# Word-final ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def word_final(seg, _):
    # check if the word ends in a coronal consonant
    return seg[-1] in word_final_inventory


# Normalization functions -----------------------------------------------------

def replace_umlauts(word, put_back=False):  # use translate()
    '''If put_back is True, put in umlauts; else, take them out!'''
    if put_back:
        word = word.replace(u'A', u'ä').replace(u'A', u'\xc3\xa4')
        word = word.replace(u'O', u'ö').replace(u'O', u'\xc3\xb6')

    else:
        word = word.replace(u'ä', u'A').replace(u'\xc3\xa4', u'A')
        word = word.replace(u'ö', u'O').replace(u'\xc3\xb6', u'O')

    return word


# Syllable functions ----------------------------------------------------------

def split_syllable(syllable):
    '''Split syllable into a tuple of its parts: onset, nucleus, and coda.'''
    syll = replace_umlauts(syllable).lower()  # put_back?
    nucleus = ''.join([v for v in syll if v in VOWELS])
    onset, nucleus, coda = syll.partition(nucleus)

    return (onset, nucleus, coda)


# Sonority functions ----------------------------------------------------------

def get_sonorities(syllabified_word):
    '''Return the specified word's sonority structure.'''
    syllables = syllabified_word.split('.')
    sonorities = []

    for syllable in syllables:

        try:
            onset, nucleus, coda = split_syllable(syllable)
            sonority = nucleus.title()  # make first character uppercase
            sonorous_syllable = onset + sonority + coda
            sonorities.append(sonorous_syllable)

        except ValueError:
            sonorities.append(u'?')

    sonorities = u'.'.join(sonorities)

    return sonorities


# Weight functions ------------------------------------------------------------

def get_weights(syllabified_word):
    '''Return the specified word's weight structure.'''
    syllables = syllabified_word.split('.')
    weights = [_get_syllable_weight(syll) for syll in syllables]
    weights = u'.'.join(weights)

    return weights


def _get_syllable_weight(syllable):
    '''Return the syllable weight of the given single syllable.'''
    CV = u'L'  # (C)V
    CVC = u'H'  # (C)VC+
    CVV = u'H'  # (C)VV+C*

    try:
        onset, nucleus, coda = split_syllable(syllable)

        # if the nucleus is long
        if len(nucleus) > 1:
            return CVV

        # if a coda is present
        elif coda:
            return CVC

        # if the syllable is light
        return CV

    except ValueError:
        return u'?'


# -----------------------------------------------------------------------------
