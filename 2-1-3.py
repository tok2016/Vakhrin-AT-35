import csv
import math
import re
import os
import matplotlib.pyplot as plt
import numpy as np
from operator import itemgetter
from jinja2 import Environment, FileSystemLoader
import pdfkit

input_sentences = {'name': 'Введите название файла: ', 'job_name': 'Введите название профессии: '}
currency_to_rub = {"AZN": 35.68, "BYR": 23.91, "EUR": 59.90, "GEL": 21.74, "KGS": 0.76, "KZT": 0.13, "RUR": 1,
                   "UAH": 1.64, "USD": 60.66, "UZS": 0.0055}


class DataSet:
    def __init__(self, file_name: str, vacancies_objects: list):
        self.file_name = file_name
        self.vacancies_objects = vacancies_objects

    def read_file(self):
        file = open(self.file_name, encoding='utf_8_sig')
        reader = csv.reader(file)
        vacancies = [line for line in reader]
        column_names = vacancies.pop(0)
        return column_names, [job for job in vacancies if len(job) == len(column_names) and job.count('') == 0]

    def get_reformed_file(self, reader: list, list_naming: list):
        descriptions = []
        for vac in reader:
            description = dict()
            for i in range(len(list_naming)):
                vac[i] = re.sub(r'\<[^>]*\>', '', vac[i])
                if vac[i].count('\n') != 0:
                    vac[i] = ", ".join(vac[i].split("\n"))
                vac[i] = ' '.join(vac[i].split())
                description[list_naming[i]] = vac[i]
            descriptions.append(Vacancy(description))
        return descriptions


class Vacancy:
    def __init__(self, descriptions: dict):
        self.name = descriptions['name']
        self.salary = Salary(descriptions)
        self.area_name = descriptions['area_name']
        self.published_at = int(descriptions['published_at'][:4])


class Salary:
    def __init__(self, descriptions: dict):
        self.salary_from = self.convert_string_to_int(descriptions['salary_from'])
        self.salary_to = self.convert_string_to_int(descriptions['salary_to'])
        self.salary_currency = descriptions['salary_currency']
        self.salary_in_rub = self.convert_to_rubles((self.salary_to + self.salary_from) / 2, self.salary_currency)

    def convert_to_rubles(self, average_salary, currency):
        return average_salary * currency_to_rub[currency]

    def convert_string_to_int(self, line: str):
        return int(line.split('.')[0])


class InputConnect:
    def __init__(self, sentences: dict):
        self.name = input(sentences['name'])
        self.job_name = input(sentences['job_name'])
        self.vacancies_info = {}
        self.vacancies_info_names = ['Динамика уровня зарплат по годам',
                                     'Динамика количества вакансий по годам',
                                     'Динамика уровня зарплат по годам для выбранной профессии',
                                     'Динамика количества вакансий по годам для выбранной профессии',
                                     'Уровень зарплат по городам (в порядке убывания)',
                                     'Доля вакансий по городам (в порядке убывания)']

    def fill_vacancies_info(self, vacancies: list):
        years = set()
        cities = dict()
        for vac in vacancies:
            years.add(vac.published_at)
            if vac.area_name in cities:
                cities[vac.area_name].append(vac.salary.salary_in_rub)
            else:
                cities[vac.area_name] = [vac.salary.salary_in_rub]
        years = sorted(years)
        years = list(range(min(years), max(years) + 1))
        cities = [city for city in cities.items() if math.floor(len(city[1]) / len(vacancies) * 100) >= 1]
        vacancies_by_year_and_city = self.get_vacancies_info_by_year(vacancies, years) + \
                                     self.get_vacancies_info_by_city(vacancies, cities)
        for i in range(len(vacancies_by_year_and_city)):
            self.vacancies_info[self.vacancies_info_names[i]] = vacancies_by_year_and_city[i]

    def get_vacancies_info_by_year(self, vacancies: list, years: list):
        all_salaries_by_year = {year: [] for year in years}
        all_vacancies_count_by_year = {year: 0 for year in years}
        exact_salaries_by_year = {year: [] for year in years}
        exact_vacancies_count_by_year = {year: 0 for year in years}
        for vac in vacancies:
            all_salaries_by_year[vac.published_at].append(vac.salary.salary_in_rub)
            all_vacancies_count_by_year[vac.published_at] += 1
            if self.job_name in vac.name:
                exact_salaries_by_year[vac.published_at].append(vac.salary.salary_in_rub)
                exact_vacancies_count_by_year[vac.published_at] += 1
        all_salaries_by_year = {year: int(sum(salaries) / len(salaries)) if len(salaries) != 0 else 0
                                for year, salaries in all_salaries_by_year.items()}
        exact_salaries_by_year = {year: int(sum(salaries) / len(salaries)) if len(salaries) != 0 else 0
                                  for year, salaries in exact_salaries_by_year.items()}
        return all_salaries_by_year, all_vacancies_count_by_year, exact_salaries_by_year, exact_vacancies_count_by_year

    def get_vacancies_info_by_city(self, vacancies: list, cities):
        all_fractions_by_city = {city[0]: round(len(city[1]) / len(vacancies), 4) for city in cities}
        all_fractions_by_city = dict(sorted(all_fractions_by_city.items(),
                                            key=itemgetter(1), reverse=True)[:10])
        cities = sorted(cities, key=lambda salaries: sum(salaries[1]) / len(salaries[1]), reverse=True)
        all_salaries_by_cities = {city[0]: int(sum(city[1]) / len(city[1])) if len(city[1]) > 0 else 0
                                  for city in cities[:min(10, len(cities))]}
        return all_salaries_by_cities, all_fractions_by_city

    def print_vacancies_info(self, vacancies: list, pdf_name: str):
        self.fill_vacancies_info(vacancies)
        for key, value in self.vacancies_info.items():
            print(f"{key}: {value}")
        rep = Report(pdf_name, self.vacancies_info, self.job_name)
        rep.generate_pdf('graph.png')


class Report:
    def __init__(self, name, years_data, job_name):
        self.name = name
        self.years_data = years_data
        self.job_name = job_name

    def generate_pdf(self, image_name: str):
        environment = Environment(loader=FileSystemLoader('.'))
        template = environment.get_template('pdf_template.html')
        years_headers = ['Год', 'Средняя зарплата', f"Средняя зарплата - {self.job_name}", 'Количество вакансий',
                         f"Количество вакансий - {self.job_name}"]
        area_headers = ['Город', 'Уровень зарплат', '', 'Город', 'Доля вакансий']
        self.generate_image(image_name)
        pdf_template = template.render({
            'pdf_title': 'style = "text-align: center; font-size: 36px"',
            'job_name': self.job_name,
            'image_file': image_name,
            'table_title': 'style = "text-align: center"',
            'cell_style': 'style = "border: 1px solid #000000; border-collapse: collapse; font-size: 18px; height: 19pt; padding: 5px; text-align: center"',
            'empty_cell': 'style = ""',
            'years_headers': years_headers,
            'years_data': self.get_years_statistics(),
            'area_headers': area_headers,
            'area_data': self.get_area_statistics()
        })
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdfkit.from_string(pdf_template, self.name, configuration=config, options={'enable-local-file-access': None})

    def generate_image(self, image_name):
        figure, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 9))
        axes = axes.flatten()
        plt.rcParams['font.size'] = '8'
        self.draw_vertical_graph(axes[0], 'Динамика уровня зарплат по годам',
                                 'Динамика уровня зарплат по годам для выбранной профессии',
                                 'Уровень зарплат по годам', 'средняя з/п', f"з/п {self.job_name.lower()}")
        self.draw_vertical_graph(axes[1], 'Динамика количества вакансий по годам',
                                 'Динамика количества вакансий по годам для выбранной профессии',
                                 'Количество вакансий по годам', 'Количество вакансий',
                                 f"Количество вакансий {self.job_name.lower()}")
        self.draw_horizontal_graph(axes[2], 'Уровень зарплат по городам (в порядке убывания)',
                                   'Уровень зарплат по городам')
        self.draw_pie_graph(axes[3], 'Доля вакансий по городам (в порядке убывания)', 'Доля вакансий по городам')
        figure.tight_layout(pad=3)
        figure.savefig(image_name)

    def draw_vertical_graph(self, year_axis, average_stats_key, job_stats_key, graph_title, average_label, job_label):
        x = np.arange(len(self.years_data[average_stats_key].keys()))
        year_axis.bar(x - 0.2, self.years_data[average_stats_key].values(), width=0.4, label=average_label)
        year_axis.bar(x + 0.2, self.years_data[job_stats_key].values(), width=0.4, label=job_label)
        year_axis.set_title(graph_title, fontsize=16)
        year_axis.set_xticks(x, self.years_data[average_stats_key].keys())
        year_axis.legend()
        year_axis.grid(axis='y')
        year_axis.tick_params(axis='x', labelrotation=90)

    def draw_horizontal_graph(self, area_axis, area_stats_key, graph_title):
        y_labels = [area.replace('-', '-\n').replace(' ', '\n') for area in self.years_data[area_stats_key].keys()]
        y = np.arange(len(y_labels))
        area_axis.barh(y, self.years_data[area_stats_key].values())
        area_axis.set_title(graph_title, fontsize=16)
        area_axis.set_yticks(y, labels=y_labels, fontsize=6, verticalalignment='center', horizontalalignment='right')
        area_axis.invert_yaxis()
        area_axis.tick_params(axis='y', labelrotation=0)
        area_axis.grid(axis='x')

    def draw_pie_graph(self, area_axis, area_stats_key, graph_title):
        plt.rcParams['font.size'] = '6'
        self.years_data[area_stats_key]['Другие'] = 1 - sum([vac for vac in self.years_data[area_stats_key].values()])
        area_axis.pie(self.years_data[area_stats_key].values(), labels=self.years_data[area_stats_key].keys())
        area_axis.axis('equal')
        area_axis.set_title(graph_title, fontsize=16)

    def get_years_statistics(self):
        return {year: [salary, job_salary, count, job_count]
                for year, salary, job_salary, count, job_count in
                zip(self.years_data['Динамика уровня зарплат по годам'].keys(),
                    self.years_data['Динамика уровня зарплат по годам'].values(),
                    self.years_data['Динамика уровня зарплат по годам для выбранной профессии'].values(),
                    self.years_data['Динамика количества вакансий по годам'].values(),
                    self.years_data['Динамика количества вакансий по годам для выбранной профессии'].values())}

    def get_area_statistics(self):
        self.years_data['Доля вакансий по городам (в порядке убывания)'] = \
            {area: str(f"{fraction * 100:,.2f}%").replace('.', ',')
             for area, fraction in self.years_data['Доля вакансий по городам (в порядке убывания)'].items()}
        return {i: [area_salary, salary, area_fractions, fractions_by_area]
                for i, (area_salary, salary, area_fractions, fractions_by_area) in
                enumerate(zip(self.years_data['Уровень зарплат по городам (в порядке убывания)'].keys(),
                              self.years_data['Уровень зарплат по городам (в порядке убывания)'].values(),
                              self.years_data['Доля вакансий по городам (в порядке убывания)'].keys(),
                              self.years_data['Доля вакансий по городам (в порядке убывания)'].values()))}


csv_file = InputConnect(input_sentences)
if os.path.getsize(csv_file.name) == 0:
    print('Пустой файл')
else:
    data = DataSet(csv_file.name, [])
    info = data.read_file()
    data.vacancies_objects = data.get_reformed_file(info[1], info[0])
    csv_file.print_vacancies_info(data.vacancies_objects, 'report.pdf')
