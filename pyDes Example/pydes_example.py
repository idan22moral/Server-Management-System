import pyDes
import os
import time

key = "my_key12"

# Create an instance of a DES encryption object
des = pyDes.des(key=key, mode=pyDes.ECB , pad=b'\0')

# ---------------text encryption-----------------

# Encrypt a text using DES
text = "this is some text\nI'm trying to show that text encryption\nis available in DES"
encrypted_text = des.encrypt(text)

# Decrypt the text using DES
decrypted_text = des.decrypt(encrypted_text).strip(b'\0')

print("\n\n---------------text encryption-----------------\n\n")
print(f"Original Text:\n\n{text}\n")
print(f"Encrypted Text:\n\n{encrypted_text}\n")
print(f"Decrypted Text:\n\n{decrypted_text.decode()}\n")
print("-----------------------------------------------\n\n")
# -----------------------------------------------


# ---------------image encryption----------------
print("---------------image encryption----------------\n\n")

# Create folder for the results
if not os.path.exists("results"):
    os.mkdir("results")

# Load the data from the image
print("Loading image data...")
image_data = open("image.png", "rb").read()

# Encrypt image data using DES
print("\nEncrypting image data...")
encryption_beginning_time = time.time()
encrypted_image_data = des.encrypt(image_data)
encryption_end_time = time.time()
print(f"Encryption took: {encryption_end_time - encryption_beginning_time}s\n")

# Save the encrypted data in .dat file
print("Saving encrypted data in file...")
open("results/encrypted_image.dat", "wb").write(encrypted_image_data)

# Decrypt image data using DES
print("\nDecrypting image data...")
decryption_beginning_time = time.time()
decrypted_image_data = des.decrypt(encrypted_image_data)
decryption_end_time = time.time()
print(f"Decryption took: {decryption_end_time - decryption_beginning_time}s\n")

# Save the decrypted data in .png file
print("Saving decrypted data in file...")
open("results/decrypted_image.png", "wb").write(decrypted_image_data)
print("\n\n-----------------------------------------------\n\n")
# -----------------------------------------------