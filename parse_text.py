import re
from usaddress import parse as address_parse
import nltk
from nltk import ne_chunk, pos_tag, word_tokenize
import string
from state_name_conversion import us_state_to_abbrev, abbrev_to_us_state


class ParseText():
    def __init__(self, text):
        self.original_text = text
        self.text = text
        self.db_dictionary = {}
        self.email = []
        self.phone = None
        self.fax = None
        self.address = []
        self.parts = {}
        self.name = []
        self.business = []
        self.website = []

    def __str__(self):
        val = {
            "OG text": self.original_text,
            "Mod text": self.text,
            "Emails": self.email,
            "Phones": self.phone,
            "address": self.address,
            "add_parts": self.parts,
            "names": self.name,
            "business": self.business
        }
        return str(val)
        

    def extract_info(self):
        self.get_email()
        self.get_phone_numbers()
        self.get_website()
        self.text = " ".join(self.text)
        self.get_address()
        self.get_name_2()
        self.get_business()
        info = {
            "email": self.email if len(self.email)>0 else None,
            "website": self.website if len(self.website)>0 else None,
            "phone": self.phone if len(self.phone)>0 else None,
            "name": self.name if len(self.name)>0 else None,
            "fax": self.fax,
            "business": self.business
            
        }
        info = info | self.parts
        self.db_dictionary = info | self.db_dictionary
        return self.db_dictionary

    def remove_text(self, vals):
        for i in vals:
            self.text = self.text.replace(i, '')
    
    # Identify email from text
    def get_email(self):
        extract_email_pattern = re.compile(r"\S+@\S+\.\S+")
        # Extract email addresses from a string
        emails_only = [match.group() for item in self.text for match in extract_email_pattern.finditer(item) if match]
        emails = list(filter(extract_email_pattern.search, self.text))
        # self.remove_text(emails)
        self.email.extend(emails_only)
        for i in emails:
            self.text.remove(i)

    def get_website(self):
        extract_website_pattern = re.compile("[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)")
        website = list(filter(extract_website_pattern.search, self.text))
        website_only = [match.group() for item in self.text for match in extract_website_pattern.finditer(item) if match]
        self.website.extend(website_only)
        for i in website:
            self.text.remove(i)
    
    def get_phone_numbers(self):
        extract_phone_number_pattern = re.compile("\\+?\\d{1,4}?[-.\\s]?\\(?\\)?[-.\\s]?\\d{1,5}[-.\\s]?\\d{4,5}")
        phone_numbers = list(filter(extract_phone_number_pattern.search, self.text))
        for i in phone_numbers:
            if 'fax' in i.lower():
                fax = re.findall(extract_phone_number_pattern, i)[0]
                self.fax = fax
            elif self.phone == None:
                phone = re.findall(extract_phone_number_pattern, i)[0]
                self.phone = phone
            self.text.remove(i)
    
    def get_names(self):
        names = []
        address_parts = address_parse(self.text)
        not_address = {i[0] for i in address_parts if i[1] == "Recipient"}
        for sent in nltk.sent_tokenize(self.text):
            for chunk in ne_chunk(pos_tag(word_tokenize(sent))):
                if hasattr(chunk, 'label') and chunk.label() == 'PERSON':
                    name = ' '.join([c[0] for c in chunk if c[0] in not_address])
                    if name != '': 
                        names.append(name)
        # self.remove_text(names)
        self.name.extend(names)
    
    def prep_address_for_db(self, parts):
        street = " ".join([i[0] for i in parts if i[1] not in ("StateName", "ZipCode", "CountryName", "PlaceName")])
        zipcode = " ".join([i[0] for i in parts if i[1] == "ZipCode"]).translate(str.maketrans('', '', string.punctuation))
        city = " ".join([i[0] for i in parts if i[1] == i[1] == "PlaceName"]).translate(str.maketrans('', '', string.punctuation))
        state = " ".join([i[0] for i in parts if i[1] == i[1] == "StateName"]).translate(str.maketrans('', '', string.punctuation))
        state_og = state
        country = " ".join([i[0] for i in parts if i[1] == i[1] == "CountryName"]).translate(str.maketrans('', '', string.punctuation))
        if state not in abbrev_to_us_state.keys() and state in abbrev_to_us_state.values():
            state = us_state_to_abbrev[state]
        return {'address': street, 'zipcode': zipcode, 'city': city, 'state': state, 'state_og': state_og, 'country': country}
    
    def get_address(self):
        address_parts = address_parse(self.text)
        address = [" ".join([i[0] for i in address_parts if i[1] != "Recipient"])]
        parts = [i for i in address_parts if i[1] != "Recipient"]
        db_parts = self.prep_address_for_db(parts)
        for part in db_parts:
            self.remove_text([db_parts[part]])
        self.remove_text(address)
        self.address.extend(address)
        self.parts = self.parts | db_parts

    def get_business(self):
        business_domain = self.email[0].split("@")[1].split(".")[0]
        self.business = business_domain.capitalize()

    def get_name_2(self):
        name  = self.email[0].split("@")[0].split(".")
        self.name = [i.capitalize() for i in name]

    def get_db_info(self):
        if len(self.name) == 2:
            fn, ln = self.name
        elif len(self.name) == 1:
            fn, ln = self.name[0], "???"
        elif len(self.name) == 0:
            fn, ln = "???", "???"
        else:
            fn, ln = " ".join(self.name[:-1]), self.name[-1]
        contact = [0,
                   fn,
                   ln, 
                   self.parts["address"],
                   self.parts["city"],
                   self.parts["state"],
                   self.parts["zipcode"],
                   self.phone,
                   self.email[0]]
        company = (self.business, 
                   self.parts["address"],
                   self.parts["city"],
                   self.parts["state"],
                   self.parts["zipcode"],
                   self.phone,
                   self.fax)
        return contact, company
        








