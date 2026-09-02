import os
import time
import pandas as pd
import uuid

class ExcelRepository:
    def __init__(self, filepath):
        self.filepath = filepath

    def get_existing_data(self):
        if not os.path.exists(self.filepath):
            return None
        return pd.read_excel(self.filepath, sheet_name=None)

    def save_history(self, new_dfs_dict):
        existing_data = self.get_existing_data()
        final_data = {}
        
        if existing_data:
            for sheet_name, df in existing_data.items():
                final_data[sheet_name] = df.copy()

        for sheet_name, new_df in new_dfs_dict.items():
            if sheet_name in final_data:
                if sheet_name == 'Info_Planta':
                    final_data[sheet_name] = new_df
                else:
                    final_data[sheet_name] = pd.concat([final_data[sheet_name], new_df], ignore_index=True)
            else:
                final_data[sheet_name] = new_df

        temp_filepath = f"{self.filepath}.{uuid.uuid4().hex}.tmp.xlsx"
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                with pd.ExcelWriter(temp_filepath, engine='openpyxl') as writer:
                    for sheet, df in final_data.items():
                        df.to_excel(writer, sheet_name=sheet, index=False)
                
                pd.read_excel(temp_filepath, sheet_name=None)
                os.replace(temp_filepath, self.filepath)
                return True
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    raise e 
            finally:
                if os.path.exists(temp_filepath):
                    try: os.remove(temp_filepath)
                    except: pass