# frut
Provide street navigation with driving fun in mind

## Overview
frut is a web application that builds on existing street navigation APIs. Its purpose is to add an additional aspect to route planning: driving fun. In order to measure the fun of a route we assume that driving is more fun the more corners there are on the route. Frut shall optimize for the shortest route with the most corners between two locations on a map.

## High level requirements
* We have to add an additional weight to each route segment that measures the curviness of the route. This is done in two steps. First we calculate each bearing difference between adjacent route sections. Then we calculate the fun index for a route segment (fidx) by calculating the average of the absolute bearing differences of the leading and the following route segment.
* The user shall be able to pick a starting point and an endpoint either from a map or by entering the addresses into input fields.
* The user shall be able to select the type of streets that the route shall be optimized for (highway, country road, bike path).
* The web app shall display the route on a map.
