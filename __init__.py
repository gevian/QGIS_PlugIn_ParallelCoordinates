# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ParallelCoordinates
                                 A QGIS plugin
 Allows interactive visual analysis using parallel coordinates.
                             -------------------
        begin                : 2014-06-28
        copyright            : (C) 2014 by Magnus Heitzler
        email                : magnus.heitzler@gmx.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    # load ParallelCoordinates class from file ParallelCoordinates
    from parallelcoordinates_plugin import ParallelCoordinates_Plugin
    return ParallelCoordinates_Plugin(iface)
