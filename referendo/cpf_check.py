def check_cpf(cpf):
    ''' This function calculates the first and second verification digit for CPF 
        cpf is a 11-digits long string. The last two digits are the verification digits
        If the CPF is correct, returns True; otherwise, returns False.
    '''
    # Since CPF standard representation is 999.999.999-99, let get rid of any
    # non-digit character.
    cpf = ''.join([char for char in cpf if char.isdigit()])
    def dgt(cpf):
       vd = 0
       for m, d in enumerate(cpf[::-1]):
           vd += (m+2) * int(d)
       vd = 11 - vd % 11
       if vd >= 10:
          vd = 0
       return (cpf + str(vd))
    recalculated = dgt(dgt(cpf[:9]))
    return True if cpf == recalculated else False

