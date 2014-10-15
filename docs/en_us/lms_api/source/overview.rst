.. _edX Learning Management System API Overview:

################################################
edX Learning Management System API Overview
################################################

The edX Learning Management System (LMS) API Overview enables you to build
applications for students to view course information and videos. 

The edX LMS API uses Representational State Transfer (REST) design principles
and supports JavaScript Object Notation (JSON) data-interchange format. Our
REST API is simple, lightweight and optimized.

You can use the edX LMS API for web, desktop, and mobile applications. 


**********************************
edX LMS API Version 0.5, Alpha
**********************************

 The edX LMS API is currently at version 0.5 and is an Alpha release. We
 plan on making significant enhancements and changes to the API. 

.. caution::
 As this is a new and rapidly evolving API, at this time edX does not guarantee
 forward compatibility. We encourage you to use and experiment with the API,
 while keeping in mind that endpoints may change.

****************************
edX LMS API Capabilities
****************************

With the edX LMS API, you can:

* Get :ref:`user details<Get User Details>` and :ref:`course enrollments<Get a
  User's Course Enrollments>` for a user.

* Get :ref:`course information<Get the Course About Page>`, :ref:`updates<Get
  Course Updates>`, and :ref:`handouts<Get Course Handouts>` for courses the
  user is enrolled in.

* Get :ref:`videos<Get the Video List>` and :ref:`transcripts<Get a Video
  Transcript>` for courses the user is enrolled in.