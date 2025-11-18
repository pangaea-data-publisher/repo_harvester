<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:sdo="http://schema.org/"
                xmlns:dcat="http://www.w3.org/ns/dcat#"
                xmlns:dct="http://purl.org/dc/terms/"
                xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">

  <xsl:output method="text" encoding="UTF-8"/>

  <xsl:template match="/">
    <xsl:text>{</xsl:text>

    <!-- Catalog metadata -->
    <xsl:text>"metadata":{</xsl:text>

    <xsl:text>"resource_type":"</xsl:text>
    <xsl:value-of select="name(*/*)"/>
    <xsl:text>",</xsl:text>

    <xsl:text>"title":"</xsl:text>
    <xsl:value-of select="*/*/sdo:name | */*/dct:title"/>
    <xsl:text>",</xsl:text>

    <xsl:text>"description":"</xsl:text>
    <xsl:value-of select="*/*/sdo:description | */*/dct:description"/>
    <xsl:text>",</xsl:text>

    <xsl:text>"language":"</xsl:text>
    <xsl:value-of select="*/*/sdo:inLanguage"/>
    <xsl:text>",</xsl:text>

    <xsl:text>"publisher":"</xsl:text>
    <xsl:value-of select="*/*/sdo:publisher//sdo:name"/>
    <xsl:text>"</xsl:text>

    <xsl:text>},</xsl:text>

    <!-- WebAPI list -->
    <xsl:text>"services":[</xsl:text>
    <xsl:for-each select="//sdo:WebAPI">
      <xsl:text>{"endpoint_uri":"</xsl:text>
      <xsl:value-of select="sdo:url"/>
      <xsl:text>"</xsl:text>
        <xsl:if test="sdo:documentation">
            <xsl:text>, "conforms_to":"</xsl:text>
             <xsl:value-of select="sdo:documentation"/>
             <xsl:text>"</xsl:text>
        </xsl:if>

      <xsl:text>}</xsl:text>
      <xsl:if test="position() != last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
    </xsl:for-each>
    <xsl:text>]</xsl:text>

    <xsl:text>}</xsl:text>
  </xsl:template>
</xsl:stylesheet>