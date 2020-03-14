from peewee import SqliteDatabase, IntegerField, CharField, TextField, ManyToManyField, Model

db = SqliteDatabase('data.db')

class BaseModel(Model):
    class Meta:
        database = db

class Stock(BaseModel):
    quantity = IntegerField(default=0)
    place = CharField()


class Pin(BaseModel):
    unit = CharField()
    pin = CharField()
    block_pin = CharField()

class Param(BaseModel):
    name = CharField()
    value = CharField()

class Mod(BaseModel):
    name = CharField()
    value = CharField()

class Prop(BaseModel):
    name = CharField()
    value = CharField()

class Part(BaseModel):
    block = CharField()
    model = CharField()
    library = CharField()
    symbol = CharField()
    datasheet = CharField()
    description = TextField(default='')
    footprint = CharField()
    params = ManyToManyField(Param, backref='parts_params')
    spice = TextField(default='')
    mods = ManyToManyField(Mod, backref='blocks')
    props = ManyToManyField(Prop, backref='blocks')
    stock = ManyToManyField(Stock, backref='parts_stock')
    pins = ManyToManyField(Pin, backref='blocks')

    def __str__(self):
        return ' '.join([str(self.id), self.block, self.model])

    @property
    def spice_params(self):
        if self.spice.upper().find('SUBCKT') != -1:
            return {}

        without_comments = filter(lambda line: line[0] != '*', self.spice)
        replace_plus_joints = ''.join(without_comments).replace('+', ' ').replace('(', ' ').replace(')', ' ').upper()
        reduce_double_spaces = ' '.join(replace_plus_joints.split()).replace(' =', '=').replace('= ', '=')
        spice_model = reduce_double_spaces.split(' ')

        params = {}
        for param in spice_model:
            if param.find('=') == -1:
                continue

            param, value = param.split('=')
            try:
                params[param] = float(value)
            except:
                params[param] = value

        return params

db.create_tables([Stock, Param, Mod, Prop, Part, Pin, Part.params.get_through_model(), Part.stock.get_through_model(), Part.mods.get_through_model(), Part.props.get_through_model(), Part.pins.get_through_model()])

