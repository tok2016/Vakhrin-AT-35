from task1_5_2 import get_vacancies_table
from task2_1_3 import get_statistics

request = input()

#ветка main

if request == 'Вакансии':
    get_vacancies_table()
elif request == 'Статистика':
    get_statistics()

