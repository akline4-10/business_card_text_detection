import mysql.connector
import getpass
import pandas as pd


class DBManager():
    def __init__(self, db_name="sql3743596", user="sql3743596", host="sql3.freesqldatabase.com"):
        password = getpass.getpass(f"Enter the {db_name} db password: ")
        self.mydb = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        self.mycursor = self.mydb.cursor()
        print("Connection made")
    
    def select_data_pandas(self, query):
        self.mycursor.execute(query)
        results = self.mycursor.fetchall()
        df_results = pd.DataFrame(results, columns=self.mycursor.column_names)
        return df_results
    
    def write_data(self, insert_query, vals):
        self.mycursor.execute(insert_query, vals)
        self.mydb.commit()

    def write_company_data(self,values):
        companies = self.select_data_pandas(f"SELECT * FROM Companies WHERE CompanyName = '{values[0]}'")
        if companies.empty:
            query = f"""INSERT INTO Companies 
                    ({",".join(list(companies.columns)[1:])})
                    VALUES ({",".join(["%s"]*len(values))});"""
            self.write_data(query, values)
            companies = self.select_data_pandas(f"SELECT * FROM Companies WHERE CompanyName = '{values[0]}'")
        return companies

    def write_contact_data(self, values, company):
        query = f"""INSERT INTO Contacts 
                    (EmployerID, FirstName, LastName, 
                    Street, City, State, ZipCode, 
                    Phone, Email)
                    VALUES ({",".join(["%s"]*len(values))});"""
        if len(company) == 1:
            values[0] = int(company.loc[0,'CompanyID'])
        else:
            mask = company[["Street", "City", "State", "ZipCode"]] == values[3:7]
            idx = int(mask.sum(axis=1).argmax())
            values[0] = int(company.loc[idx,'CompanyID'])
        print(tuple(values))
        self.write_data(query, tuple(values))

    def add_business_card_info_to_db(self, business_data, contact_data):
        business = self.write_company_data(business_data)
        contact = self.write_contact_data(contact_data, business)
        print("Saved to database")

    def close_connection(self):
        self.mydb.close()
        print("Connection closed")
    
