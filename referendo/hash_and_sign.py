from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import hashlib
from datetime import datetime, timezone

#### BEFORE signer.save()   #
def hash_and_sign_data(signer):
    ''' This is the function to be called before signer data is
        saved and commited. This function returns the hash and
        this signature, both of with will be saved to the database
        in their own fields, signer.hash and signer.signature
    '''
    with open("referendum_private_key.pem", "rb") as f:
       private_key = serialization.load_pem_private_key(
          f.read(), password=None)

    str_to_hash = (f"{signer.signer_full_name}"
                   f"{signer.gender}"
                   f"{signer.signer_birthdate}"
                   f"{signer.signer_cpf}"
                   f"{signer.voter_id}"
                   f"{signer.email}"
                   f"{signer.signer_mobile_number}"
                   f"{signer.signing_datetime}"
                   f"{signer.originating_ip}")

    hashed_string = hashlib.sha256(str_to_hash.encode()).hexdigest()
    signature = private_key.sign(
        hashed_string.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
       hashes.SHA256()
    )
    return hashed_string, signature

