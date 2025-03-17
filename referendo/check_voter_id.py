def check_voter_dv(voter_id):
    ''' 
    Checks voter_id validity based on the double check digits
    Typical formatting is '9999 9999 9999' or '9999.9999.9999', so
        weeds out any non-digit character
    '''

    voter_id = ''.join([char for char in voter_id if char.isdigit()])
    if len(voter_id) < 12:
        return False

    sequential = voter_id[:8]
    uf = voter_id[8:10]  # This indicates the state where voter votes
    vd1 = 0
    vd2 = 0
    summation = 0
    factor = 9
    for digit in sequential[::-1]:
        summation += int(digit) * factor
        factor -= 1
    remainder = summation % 11 
    if remainder == 10:
       vd1 = 0
    elif remainder == 0 and (uf == "01" or uf == "02"):
       vd1 = 1
    else:
       vd1 = remainder

    summation = 0
    factor = 7
    for digit in (uf + str(vd1)):
        summation += int(digit) * factor
        factor += 1
    remainder = summation % 11
    if remainder == 10:
       vd2 = 0
    elif remainder == 0 and (uf == "01" or uf == "02"):
       vd2 = 1
    else:
       vd2 = remainder

    return True if voter_id[-2:] == f"{vd1}{vd2}" else False


