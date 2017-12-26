################################
Certificate authority management
################################

**django-ca** supports managing multiple certificate authorities as well as child certificate
authorities.

The :doc:`command-line interface </cli/intro>` is the only way to create certificate authorities.  It is
obviously most important that the private keys are never exposed to any attacker, and any web interface would
pose an unnecessary risk. Some details, like the x509 extensions used for signing certificates, can be
configured using the web interface.

For the same reason, the private key of a certificate authority is stored on the filesystem and not
in the database. The initial location of the private key is configured by the :ref:`CA_DIR setting
<settings-ca-dir>`. This also means that you can run your **django-ca** on two hosts, where one
host has the private key and only uses the command line, and one with the webinterface that can
still be used to revoke certificates.

*****************
Index of commands
*****************

To manage certificate authorities, use the following `manage.py` commands:

========== ======================================================
Command    Description
========== ======================================================
dump_ca    Write the CA certificate to a file.
edit_ca    Edit a certificate authority.
import_ca  Import an existing certificate authority.
init_ca    Create a new certificate authority.
list_cas   List all currently configured certificate authorities.
view_ca    View details of a certificate authority.
========== ======================================================

Like all `manage.py` subcommands, you can run ``manage.py <subcomand> -h`` to get a list of availabble
parameters.

***************
Create a new CA
***************

You should be very careful when creating a new certificate authority, especially if it is used by a large
number of clients. If you make a mistake here, it could make your CA unusable and you have to redistribute new
public keys to all clients, which is usually a lot of work.

Please think carefully about how you want to run your CA: Do you want intermediate CAs? Do you want to use
CRLs and/or run an OCSP responder?

``pathlen`` attribute
=====================

The ``pathlen`` attribute says how many levels of intermediate CAs can be used below a given CA. If present,
it is an integer attribute (>= 0) meaning how many intermediate CAs can be below this CA. If *not* present,
the number is unlimited. For a valid setup, all ``pathlen`` attributes of all intermediate CAs must be
correct. Here is a typical (correct) example::

   root   # pathlen: 2
   |- child_A  # pathlen 1
      |- child_A.1  # pathlen 0
   |- child_B  # pathlen 0

In this example, `root` and `child_A` can have intermediate CAs, while `child_B` and `child_A.1` can
not.

The default value for the ``pathlen`` attribute is ``0``, meaning that any CA cannot have any intermediate
CAs. You can use the ``--pathlen`` parameter to set a different value or the ``--no-pathlen`` parameter if you
don't want to set the attribute::

   # Two sublevels of intermediate CAs:
   python manage.py init_ca --pathlen=2 ...

   # unlimited number of intermediate CAs:
   python manage.py init_ca --no-pathlen ... 

CRL URLs
========

Certificate Revocation Lists (CRLs) are signed files that contain a list of all revoked certificates.
Certificates (including those for CAs) can contain pointers to CRLs, usually a single URL, in the
``crlDistributionPoints`` extension. Clients that support this extension can query the URL and refuse to
establish a connection if the certificate is revoked.

Since a CRL has to be signed by the issuing CA, root CAs cannot sensibly contain a CRL: You could only revoke
the root CA with it, and it would have to be signed by the (compromised) root CA.

**django-ca** supports adding CRLs to (intermediate) CAs as well as end-user certificates. The former cannot
be changed later, while the latter can be changed at any time for future certificates using the ``edit_ca``
subcommand or via the web interface. 

.. WARNING:: 

   If you decide to add a CRL to CAs/certificates, you must also provide the CRLs at the given URL.
   **django-ca** provides everything you need, please see :doc:`/crl` for more information.

For certificates to be signed by this CA, use the ``--crl-url`` option::

   python manage.py init_ca --ca-url http://ca.example.com/example.crl ...

To add a CRL url for an intermediate CA, use the ``--ca-crl-url`` option::

   python manage.py init_ca \
      --parent root
      --ca-url http://ca.example.com/root.crl
      ...

OCSP responder
==============

The `Online Certificate Status Protocol <https://en.wikipedia.org/wiki/Online_Certificate_Status_Protocol>`_
or OCSP is a service (called "OCSP responder") run by a certificate authority that allows clients to query for
revoked certificates. It is an improvement over CRLs particulary for larger CAs because a full CRL can grow
quite big. 

The same restrictions as for CRLs apply: You cannot add a OCSP URL to a root CA, it runs via HTTP (not HTTPS)
and if you decide to add such URLs, you also have to actually run that service, or clients will refuse to
connect. **django-ca** includes a somewhat tested OCSP responder, see :doc:`/ocsp` for more information.

To add a OCSP URL to certificates to be signed by this CA, use the ``--ocsp-url`` option::

   python manage.py --ocsp-url http://ocsp.ca.example.com/example ...

To add a OCSP URL to intermediate CAs, use the ``--ca-ocsp-url`` option::

   python manage.py init_ca \
      --parent root \
      --ca-ocsp-url http://ocsp.ca.example.com/root \
      ...

.. _name_constraints:

Name constraints
================

NameConstraints are a little-used extension (see `RFC 5280, section 4.2.1.10
<https://tools.ietf.org/html/rfc5280#section-4.2.1.10>`_ that allows you to create CAs that are limited to
issuing certificates for a particular set of addresses. The parsing of this syntax is quite complex, see e.g.
`this blog post
<https://www.sysadmins.lv/blog-en/x509-name-constraints-certificate-extension-all-you-should-know.aspx>`_ for
a good explanation.

.. WARNING:: 

   This extension is marked as "critical". Any client that does not understand this extension will refuse a
   connection.

To add name constraints to a CA, use the ``--name-constraint`` option, which can be given multiple times.
Values are any valid name, see :ref:`names_on_cli` for detailed documentation.  Prefix the value with either
``permitted,`` or ``excluded,`` to add them to the Permitted or Excluded subtree::

   python manage.py init_ca \
      --name-constraint permitted,DNS:com
      --name-constraint permitted,DNS:net
      --name-constraint excluded,DNS:evil.com
      ...

This will restrict the CA to issuing certificates for .com and .net subdomains, except for evil.com, which
obviously should never have a certificate (evil.net is good, though).

Examples
========

Here is a shell session that illustrates the respective manage.py commands:

.. code-block:: console

   $ python manage.py init_ca --pathlen=2
   >     --crl-url=http://ca.example.com/crl \
   >     --ocsp-url=http://ocsp.ca.example.com \
   >     --issuer-url=http://ca.example.com/ca.crt \
   >     TestCA /C=AT/L=Vienna/L=Vienna/O=Example/OU=ExampleUnit/CN=ca.example.com
   $ python manage.py list_cas
   BD:5B:AB:5B:A2:1C:49:0D:9A:B2:AA:BC:68:ED:ED:7D - TestCA

   $ python manage.py view_ca BD:5B:AB:5B:A2
   ...
   * OCSP URL: http://ocsp.ca.example.com
   $ python manage.py edit_ca --ocsp-url=http://new-ocsp.ca.example.com \
   >     BD:5B:AB:5B:A2
   $ python manage.py view_ca BD:5B:AB:5B:A2
   ...
   * OCSP URL: http://new-ocsp.ca.example.com

Note that you can just use the start of a serial to identify the CA, as long as
that still uniquely identifies the CA.

***********************
Create intermediate CAs
***********************

Intermediate CAs are created, just like normal CAs, using ``manage.py init_ca``. For intermediate
CAs to be valid, CAs however must have a correct ``pathlen`` x509 extension. Its value is an
integer describing how many levels of intermediate CAs a CA may have. A ``pathlen`` of "0" means
that a CA cannot have any intermediate CAs, if it is not present, a CA may have an infinite number
of intermediate CAs.

.. NOTE:: **django-ca** by default sets a ``pathlen`` of "0", as it aims to be secure by default.
   The ``pathlen`` attribute cannot be changed in hindsight (not without resigning the CA). If you
   plan to create intermediate CAs, you have to consider this when creating the root CA.

So for example, if you want two levels of intermediate CAs, , you'd need the following ``pathlen``
values (the ``pathlen`` value is the minimum value, it could always be a larger number):

===== ==================== ======= ========================================================
index CA                   pathlen description
===== ==================== ======= ========================================================
1     example.com          2       Your root CA.
2     sub1.example.com     1       Your first intermediate CA, a sub-CA from (1).
3     sub2.example.com     0       A second intermediate CA, also a sub-CA from (1).
4     sub.sub1.example.com 0       An intermediate CA of (2).
===== ==================== ======= ========================================================

If in the above example, CA (1) had ``pathlen`` of "1" or CA (2) had a ``pathlen`` of "0", CA (4)
would no longer be a valid CA.

By default, **django-ca** sets a ``pathlen`` of 0, so CAs will not be able to have any intermediate
CAs. You can configure the value by passing ``--pathlen`` to ``init_ca``:

.. code-block:: console

   $ python manage.py init_ca --pathlen=2 ...

When creating a sub-ca, you must name its parent using the ``--parent`` parameter:

.. code-block:: console

   $ python manage.py list_cas
   BD:5B:AB:5B:A2:1C:49:0D:9A:B2:AA:BC:68:ED:ED:7D - Root CA
   $ python manage.py init_ca --parent=BD:5B:AB:5B ...

.. NOTE:: Just like throughout the system, you can always just give the start of the serial, as
   long as it still is a unique identifier for the CA.
