# !/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Filename: sqla.py
# Project: mixins
# Author: Brian Cherinka
# Created: Wednesday, 13th February 2019 3:49:07 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2019 Brian Cherinka
# Last Modified: Wednesday, 13th February 2019 5:59:17 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
import inspect
import decimal
from sqlalchemy import func, bindparam, text
from sqlalchemy.ext.declarative.api import DeclarativeMeta
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import or_, and_, not_, sqltypes, between
from operator import le, ge, gt, lt, eq, ne

from boolean_parser import BooleanParserException
from boolean_parser.conditions import Condition, BoolNot, BoolOr, BoolAnd

opdict = {'<=': le, '>=': ge, '>': gt, '<': lt, '!=': ne, '==': eq, '=': eq}


class SQLAMixin(object):
    ''' '''

    def _check_models(self, classes):
        ''' Check the input modelclass format
        
        Checks if input classes is a module of modelclasses, a list of modelclasses
        or a single ModelClass and returns a list of ModelClass objects. 
        
        Parameters:
            classes (object):
                A ModelClass module, list of models, or single ModelClass

        Returns:
            A list of ModelClasses
        '''

        # an entire module of classes
        if inspect.ismodule(classes):
            # an entire module of classes
            models = [i[1] for i in inspect.getmembers(
                classes, inspect.isclass) if hasattr(i[1], '__tablename__')]
        elif isinstance(classes, (list, tuple)):
            # a list of ModelClasses
            models = classes
        else:
            # assume a single ModelClass
            models = [classes]

        # check for proper modelclasses
        allmeta = all([isinstance(m, DeclarativeMeta) for m in models])
        assert allmeta is True, 'All input classes must be of type SQLAlchemy ModelClasses'

        return models

    def _get_field(self, modelclass, field_name, base_name=None):
        ''' Return a SQLAlchemy attribute from a field name.

        Checks that a given model contains the named field.         

        Parameters:
            modelclass (ModelClass):
                A SQLAlchemy ModelClass
            field_name (str):
                The database field name
            base_name (str):
                The database table name
        
        Returns:
            An SQLA instrumented attribute object
        '''

        field = None
        # Handle hierarchical field names such as 'parent.name'
        if base_name:
            if base_name in modelclass.__tablename__:
                field = getattr(modelclass, field_name, None)
        else:
            # Handle flat field names such as 'name'
            field = getattr(modelclass, field_name, None)

        return field
    
    def filter(self, modelclass):
        ''' Return the condition as an SQLalchemy query condition
        
        Loops over all models and creates a filter condition for that model
        given the input filter parameters.

        Parameters:
            modelclass (objects):
                A set of ModelClasses to use in the filter condition

        Returns:
            A SQL query filter condition
        '''
 
        assert modelclass is not None, 'No input found'

        condition = None
        models = self._check_models(modelclass)

        for model in models:
            # get the SQLA instrumented attribute
            field = self._get_field(model, self.name, base_name=self.base)

            # if there is an attribute then break and use that model
            if field and hasattr(field, 'type') and hasattr(field, 'ilike'):
                break

        # raise if no attribute found
        if not field:
            raise BooleanParserException(f'Table {model.__tablename__} does not have field {self.name}')

        # produce the SQLA filter condition
        condition = self._filter_one(model, field=field, condition=condition)

        return condition

    def _filter_one(self, model, field=None, condition=None):
        ''' Create a single SQLAlchemy filter condition '''

        # if no field present return the original condition
        if not field:
            return condition

        # Prepare field and value
        lower_field, lower_value, lower_value_2 = self._bind_and_lower_value(field)

        return condition

    def _bind_and_lower_value(self, field):
        ''' Bind and lower the value based on field type'''

        lower_value_2 = None

        # get python field type
        ftypes = [float, int, decimal.Decimal]
        fieldtype = field.type.python_type

        # format the values
        value, lower_field = self._format_value(self.value, fieldtype, field)
        if hasattr(self, 'value2'):
            value2, lower_field = self._format_value(self.value2, fieldtype, field)

        # bind the parameter value to the parameter name
        boundvalue = bindparam(self.bindname, value)
        lower_value = func.lower(boundvalue) if fieldtype not in ftypes else boundvalue
        if hasattr(self, 'value2'):
            self.bindname = '{0}_{1}'.format(self.fullname, 2)
            boundvalue2 = bindparam(self.bindname, value2)
            lower_value_2 = func.lower(boundvalue2) if fieldtype not in ftypes else boundvalue2

        return lower_field, lower_value, lower_value_2

    def _bind_parameter_names(self):
        ''' Bind the parameters names to the values '''

        if self.fullname not in params:
            params.update({self.fullname: self.value})
            self.bindname = self.fullname
        else:
            count = list(params.keys()).count(self.fullname)
            self.bindname = '{0}_{1}'.format(self.fullname, count)
            params.update({self.fullname: self.value})
            
    def _format_value(self, value, fieldtype, field):
        ''' Formats the value based on the fieldtype
        
        Formats the value to proper numreical type and lowercases
        the field for string fields.
        
        Parameters:
            value (str):
                The conditional value to format
            fieldtype (object):
                The python field type
            field (SQLA attribute):
                SQLA instrumented attribute

        Returns:
            The formatted value and lowercase field
        '''

        lower_field = field
        if fieldtype == float or fieldtype == decimal.Decimal:
            out_value = self._cast_value(value, datatype=float)
        elif fieldtype == int:
            out_value = self._cast_value(value, datatype=int)
        else:
            lower_field = func.lower(field)
            out_value = value

        return out_value, lower_field

    def _cast_value(self, value, datatype=float):
        ''' Cast a value to a specific Python type

        Parameters:
            value (int|float):
                A numeric value to cast to a float or integer
            datatype (object):
                The numeric cast function.  Can be either float or int.
        
        Returns:
            The value explicitly cast to an integer or float
        '''

        assert datatype in [float, int], 'datatype must be either float or int'

        try:
            out = datatype(value)
        except (ValueError, SyntaxError):
            raise BooleanParserException(f'Field {self.name} expects a {datatype.__name__} value.  Received {value} instead.')
        else:
            return out


class SQLACondition(SQLAMixin, Condition):
    ''' '''
    pass


class SQLANot(BoolNot):
    ''' SQLalchemy class for Boolean Not '''

    def filter(self, modelclass):
        return not_(self.condition.filter(modelclass))


class SQLAAnd(BoolAnd):
    ''' SQLalchemy class for Boolean And '''

    def filter(self, modelclass):
        conditions = [condition.filter(modelclass) for condition in self.conditions]
        return and_(*conditions) 


class SQLAOr(BoolOr):
    ''' SQLalchemy class for Boolean Or '''

    def filter(self, modelclass):
        conditions = [condition.filter(modelclass) for condition in self.conditions]
        return or_(*conditions)
