import dices


generator = dices.DicesGenerator()
generator.parse('d10')
print(generator.sample())
print(generator.get_warnings())
