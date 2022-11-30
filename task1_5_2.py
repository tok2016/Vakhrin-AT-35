import csv
import re
import os
from prettytable import PrettyTable, ALL

columns_max_length = 20

title_translations = ['№', 'Название', 'Описание', 'Навыки', 'Опыт работы', 'Премиум-вакансия', 'Компания',
                      'Оклад', 'Название региона', 'Дата публикации вакансии']
title_translations1 = {'№': '№', 'name': 'Название', 'description': 'Описание', 'key_skills': 'Навыки',
                       'experience_id': 'Опыт работы', 'premium': 'Премиум-вакансия', 'employer_name': 'Компания',
                       'salary_from': '', 'salary_to': 'Оклад', 'salary_gross': 'Оклад указан до вычета налогов',
                       'salary_currency': 'Идентификатор валюты оклада', 'area_name': 'Название региона',
                       'published_at': 'Дата публикации вакансии'}
experience_translations = {'noExperience': 'Нет опыта', 'between1And3': 'От 1 года до 3 лет',
                           'between3And6': 'От 3 до 6 лет', 'moreThan6': 'Более 6 лет'}
currency_translations = {'AZN': 'Манаты', 'BYR': 'Белорусские рубли', 'EUR': 'Евро', 'GEL': 'Грузинский лари',
                         'KGS': 'Киргизский сом', 'KZT': 'Тенге', 'RUR': 'Рубли', 'UAH': 'Гривны', 'USD': 'Доллары',
                         'UZS': 'Узбекский сум'}
formatters = {
    'translate_experience': lambda value, row: experience_translations[value]
    if value in experience_translations else value,
    'reform_skills': lambda value, row: cut_string(value) if len(value) > 100 else value,
    'cut_column': lambda value, row: cut_string(value) if type(value) == str and len(value) > 100 else value,
    'reform_salary': lambda value, row: f"{reform_number(value)} - {reform_number(row['salary_to'])} "
                                        f"({currency_translations[row['salary_currency']]}) "
                                        f"({is_tax_included(row['salary_gross'])})",
    'reform_publication_date': lambda value, row: reform_date(value[0:10]),
    'other': lambda value, row: value
}
vacancies_functions = {'Опыт работы': 'translate_experience', 'Навыки': 'reform_skills',
                       'Дата публикации вакансии': 'reform_publication_date', 'Оклад': 'reform_salary'}

translate_bool_string = lambda statement: 'Да' if statement == 'True' else 'Нет'
is_tax_included = lambda statement: 'Без вычета налогов' if statement == 'Да' else 'С вычетом налогов'
cut_string = lambda line: line.replace(line[100::], '...')
reform_table = lambda data, separator: [] if len(data) == 0 else data.split(separator)


def csv_reader(file_name):
    file = open(file_name, encoding='utf_8_sig')
    reader = csv.reader(file)
    vacancies = []
    for line in reader:
        vacancies.append(line)
    column_names = vacancies.pop(0)
    full_vacancies = []
    for job in vacancies:
        if len(job) == len(column_names) and job.count('') == 0:
            full_vacancies.append(job)
    return column_names, full_vacancies


def check_skills(filter_skills: list, original: list):
    return all(skill in original for skill in filter_skills)


def parse_filter_string(param: str):
    new_data = param.split(': ')
    return new_data


def csv_filer(reader, list_naming, filter_parameter, reformed):
    descriptions = []
    number = 1
    for vac in reader:
        vac_index = reader.index(vac)
        descriptions.append({'№': number})
        for i in range(len(list_naming)):
            vac[i] = re.sub(r'\<[^>]*\>', '', vac[i])
            if vac[i].count('\n') != 0:
                if list_naming[i] == 'key_skills':
                    vac[i] = "# ".join(vac[i].split("\n"))
                else:
                    vac[i] = ", ".join(vac[i].split("\n"))
            vac[i] = ' '.join(vac[i].split())
            if vac[i] == 'False' or vac[i] == 'True':
                vac[i] = translate_bool_string(vac[i])
            if filter_parameter != '' and reformed[0] == title_translations1[list_naming[i]]:
                if not (reformed[0] == 'Навыки' and check_skills(reformed[1].split(', '), vac[i].split('# ')) or
                        reformed[0] == 'Оклад' and f1(vac[i - 1]) <= int(reformed[1]) <= f1(vac[i]) or
                        reformed[0] == 'Идентификатор валюты оклада' and
                        reformed[1] in currency_translations.values() or
                        reformed[0] == 'Дата публикации вакансии' and reformed[1] == reform_date(vac[i]) or
                        reformed[0] == 'Опыт работы' and reformed[1] == experience_translations[vac[i]] or
                        reformed[1] == vac[i]):
                    number -= 1
                    break
            descriptions[vac_index][list_naming[i]] = vac[i]
        number += 1
    return descriptions


def f1(line: str):
    return int(line.split('.')[0])


def formatter(row: dict):
    i = 0
    result = {}
    for key, value in row.items():
        if key != 'salary_to' and key != 'salary_currency' and key != 'salary_gross':
            new_key = title_translations[i]
            if new_key == 'Навыки':
                value = value.replace('# ', '\n')
            else:
                value = formatters['cut_column'](value, row)
            if new_key in vacancies_functions:
                result[new_key] = formatters[vacancies_functions[new_key]](value, row)
            else:
                result[new_key] = formatters['other'](value, row)
            i += 1
    return result


def reform_number(number: str):
    if len(number) != 0 and number[0].isdigit():
        return '{:,}'.format(round(float(number))).replace(',', ' ')
    return number


def reform_date(date: str):
    dates = date.split('-')
    temp = dates[0]
    dates[0] = dates[len(dates) - 1]
    dates[len(dates) - 1] = temp
    return '.'.join(dates)


def print_vacancies(data_vacancies, dic_naming, row_numbers, columns):
    table = PrettyTable(dic_naming)
    table.align = "l"
    table.hrules = ALL
    table.max_width = columns_max_length
    flag = False
    for vac in data_vacancies:
        if len(vac) == 13:
            vac = formatter(vac)
            table.add_row(vac.values())
            flag = True
    if flag:
        print(get_cut_table(table, row_numbers, columns))
    else:
        print('Ничего не найдено')


def get_cut_table(table, row_numbers, columns):
    rows_data = reform_table(row_numbers, ' ')
    columns_data = reform_table(columns, ', ')
    if len(columns_data) > 0:
        field = ['№'] + columns_data
    else:
        field = columns_data
    if len(rows_data) == 1:
        return table.get_string(start=int(rows_data[0]) - 1, fields=field)
    elif len(rows_data) == 2:
        return table.get_string(start=int(rows_data[0]) - 1,
                                end=int(rows_data[1]) - 1, fields=field)
    return table.get_string(fields=field)


def get_vacancies_table():
    name = input('Введите название файла: ')
    filter_parameter = input('Введите параметр фильтрации: ')
    row_numbers = input('Введите количесвто строк: ')
    columns = input('Введите названия столбцов: ')
    reformed = parse_filter_string(filter_parameter)
    if os.path.getsize(name) == 0:
        print('Пустой файл')
    elif len(csv_reader(name)[1]) == 0:
        print('Нет данных')
    elif filter_parameter.count(': ') == 0 and filter_parameter != '':
        print('Формат ввода некорректен')
    elif not reformed[0] in title_translations1.values():
        print('Параметр поиска некорректен')
    else:
        info = csv_reader(name)
        print_vacancies(csv_filer(info[1], info[0], filter_parameter, reformed),
                        title_translations, row_numbers, columns)
