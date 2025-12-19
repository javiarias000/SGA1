import unicodedata

def normalize_name(name):
    # Handle specific known typos
    name = name.replace('Rafel', 'Rafael')
    
    # Normalize unicode characters
    nfkd_form = unicodedata.normalize('NFKD', name)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return only_ascii.lower()

def levenshtein_distance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def similarity_ratio(s1, s2):
    len_s1 = len(s1)
    len_s2 = len(s2)
    if len_s1 == 0 and len_s2 == 0:
        return 1.0
    if len_s1 == 0 or len_s2 == 0:
        return 0.0
    distance = levenshtein_distance(s1, s2)
    return (len_s1 + len_s2 - distance) / (len_s1 + len_s2)
