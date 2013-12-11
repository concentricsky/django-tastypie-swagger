Synopsis
========

**django-tastypie-swagger** is a small adapter library to construct Swagger_ documentation from Tastypie_ resources.

This package provides two things:

1. An embedded instance of `Swagger UI`_ to point a URL to.
2. Automatic `Resource Listing`_ and `API Declaration`_ generation that is consumed by #1


Usage
=====

Install package::

    pip install django-tastypie-swagger

Add to INSTALLED_APPS::

    INSTALLED_APPS = [
        ...

        'tastypie_swagger',

        ...
    ]

Define **TASTYPIE_SWAGGER_API_MODULE** in your settings.  It should be a python path to your instance of tastypie.api.Api_::

    TASTYPIE_SWAGGER_API_MODULE = 'mainsite.urls.api'

Include in your urlconf with namespace **tastypie_swagger**::

    urlpatterns = patterns('',
        ...

        url(r'api/doc/', include('tastypie_swagger.urls', namespace='tastypie_swagger')),

        ...
    )


Swagger documentation will be served up at the URL you configured.

Configuration
-------------------------

The following configuration variables can be set inside ``settings.py`` to
configure this application.

TASTYPIE_SWAGGER_APP_NAME
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'swagger'``

Changes the name of the application in the documentation view. This is also used in the title of the documentation view in the form of ``{{ NAME|title }} API Documentation``.

TASTYPIE_SWAGGER_APP_LINK
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'/'``

Changes where the application name is linked to in the documentation view.

TASTYPIE_SWAGGER_SHOW_DEV
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``False``

Show or hide the example documentation links.

TASTYPIE_SWAGGER_KEY_NAME
~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``'apiKey'``

Change the name of the api key that will be passed to requests.

TASTYPIE_SWAGGER_API_KEY
~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``''`` (empty string)

Prefills an example api key in the documentation view.

Detecting required fields
-------------------------

Tastypie 0.9.11 **ModelResource** fields do not respect the *blank* attribute on django model fields, which this library depends on to determine if a field is required or not.

You can use `this ModelResource subclass <https://gist.github.com/4041352>`_ as a workaround to this issue.





.. _Swagger: http://swagger.wordnik.com/
.. _Tastypie: https://django-tastypie.readthedocs.org
.. _Resource Listing: https://github.com/wordnik/swagger-core/wiki/Resource-Listing
.. _API Declaration: https://github.com/wordnik/swagger-core/wiki/API-Declaration
.. _Swagger UI: https://github.com/wordnik/swagger-ui
.. _tastypie.api.Api: https://django-tastypie.readthedocs.org/en/latest/api.html
