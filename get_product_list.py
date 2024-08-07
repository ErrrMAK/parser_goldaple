import os
import pandas as pd
import logging
import time
from tqdm import tqdm

from api_requests import get_cnt_pages_list, download_list
import db

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Функция для получения содержимого списка продуктов
def get_content_list(list):
    data = list
    
    products_list = []
    for product in data['data']['products']:
        # courier, store_pickup = get_item(product['itemId']) # Закомментировал, так отказались из-за скорости работы
        courier, store_pickup = None, None
        product_info = {
            'item_id': product['itemId'],
            'mainVariantItemId': product['mainVariantItemId'],
            'brand': product['brand'],
            'name': product['name'],
            'actual_amount': product['price']['actual']['amount'] if product['price']['actual'] is not None else None,
            'old_amount': product['price']['old']['amount'] if product['price']['old'] is not None else None,
            'link': f'https://goldapple.ru{product["url"]}',
            'courier': courier,
            'store_pickup': store_pickup, # TODO: удалить
        }
        products_list.append(product_info)

    return products_list

def clean_for_excel(text):
    if not isinstance(text, str):
        return text
    return ''.join(char for char in text if char == '\t' or char == '\n' or char == '\r' or 0x20 <= ord(char) <= 0x7E or ord(char) > 0x7F)

def save_df_to_excel(df):
    # Проверяем, существует ли папка 'result'
    if not os.path.exists('result'):
        # Если нет, создаем ее
        os.makedirs('result')

    # Очищаем DataFrame от недопустимых символов
    for col in df.columns:
        if df[col].dtype == object:  # Если столбец содержит строки
            df[col] = df[col].apply(clean_for_excel)

    # Теперь мы можем безопасно сохранить наш DataFrame в файл Excel
    df.to_excel('result/products.xlsx', index=False)


def main():
    connection = db.connection()

    # Получаем количество страниц с продуктами
    total_pages = get_cnt_pages_list() // 24

    # Создаем пустой DataFrame
    df = pd.DataFrame()
    df_list = []

    start_time = time.time()  # Запоминаем время начала выполнения цикла
    # for page_num in tqdm(range(1, 1 + 1)): 
    for page_num in tqdm(range(1, total_pages + 1)): 
        logging.info(f'Start processing page {page_num}')
        list = download_list(page_num)
        time.sleep(1)
        products_list = get_content_list(list)
        df_list.append(pd.DataFrame(products_list))
    df = pd.concat(df_list, ignore_index=True).drop_duplicates(subset=['item_id'], keep='last')

        # Получаем данные из базы данных
    details_columns, details_data = db.get_details_and_new_link_by_article(connection)
    details = pd.DataFrame(details_data, columns=details_columns)
    details['item_id'] = details['item_id'].astype(str)
    # Объединяем products_data_df и details
    products_data_df = pd.merge(df, details, on='item_id', how='left')    
    # logging.info(f'Finished processing page {page_num}')

    end_time = time.time()  # Запоминаем время окончания выполнения цикла
    logging.info(f'Total time for processing {total_pages} pages: {end_time - start_time} seconds')


    # Вызываем функцию для сохранения DataFrame в файл Excel
    save_df_to_excel(products_data_df)
    db.close_connection(connection)



if __name__ == '__main__':
    main()

#  pyinstaller .\get_product_list.py --onefile
