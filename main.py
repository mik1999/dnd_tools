import click

import alchemy.components_manager as cm
import alchemy.parameters_manager as pm
import alchemy.potion


cm = cm.ComponentsManager()
pm = pm.ParametersManager()
last_potion = None


@click.group()
def entrypoint():
    pass


@entrypoint.group('comp', help='Работа с компонентами')
def components():
    pass


@components.command('list', help='Перечислить все компоненты')
@click.option('-a', '--alias', is_flag=True, help='Указывать синонимы компонент')
@click.option('-p', '--param', is_flag=True, help='Указывать вектора параметров компонент')
def components_list(alias, param):
    print(cm.components_list(alias, param))


@components.command('descr', help='Перечислить все компоненты')
@click.argument('component_name', type=click.STRING)
def components_list(component_name):
    try:
        print(cm.info(component_name, pm))
    except cm.UnrecognizedComponent:
        print(f'Компоненты с именем {component_name} не существует.')


@entrypoint.group('param', help='Работа с параметрами')
def parameters():
    pass


@parameters.command('list', help='Список параметров')
def params_list():
    print(pm.parameters_list())


@parameters.command('culc', help='Подсчитать эффект параметра')
@click.argument('parameter_symbol', type=click.STRING)
@click.argument('value', type=click.INT)
def params_list(parameter_symbol, value):
    try:
        parameter = pm.get_param(parameter_symbol)
        print(parameter.positive.name_rus + ': ' + pm.param_description(parameter.symbol, value))
        print(parameter.negative.name_rus + ': ' + pm.param_description(parameter.symbol, -value))
    except pm.NoSuchParameter:
        print(f'Не существует параметра с таким "{parameter_symbol}" символом.')


@entrypoint.group('potion', help='Работа с зельями')
def potions():
    pass


@potions.command('mix', help='Готовка зелья, "3 светогриб + зверобой"')
@click.argument('formula', type=click.STRING)
@click.option('-s', '--save', help='Имя для сохранения зелья')
@click.option('-f', '--force', is_flag=True, help='Разрешить перезапись зелья')
def mix(formula, save, force):
    potion = alchemy.potion.Potion(cm, pm)
    try:
        if save:
            potion.name = save
        potion.mix_from(formula)
        print(potion.overall_description())
        if save:
            potion.name = save
            try:
                potion.write(force_flag=force)
                print(f'Зелье успешно сохранено как {save + ".json"}')
            except FileExistsError:
                print('Зелье с таким названием уже существует. Используйте флаг -f чтобы перезаписать')

    except alchemy.potion.ParsingFormulaError as ex:
        print('Ошибка чтения введенного рецепта: ' + ex.message)


@potions.command('descr', help='Описание сохраненного зелья')
@click.argument('potion_name', type=click.STRING)
def potion_description(potion_name):
    try:
        potion = alchemy.potion.Potion(cm, pm)
        potion.read(potion_name)
        print(potion.overall_description())
    except FileNotFoundError:
        print(f'Зелья с названием "{potion_name}" не существует.')


@potions.command('list', help='Список всех сохраненных зелий')
def potions_list():
    print(alchemy.potion.Potion.potions_list(cm, pm))


if __name__ == '__main__':
    entrypoint()
