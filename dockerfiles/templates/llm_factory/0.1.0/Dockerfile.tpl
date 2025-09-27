# syntax=docker/dockerfile:1.4

ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE} AS final

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# -- Base image metadata
LABEL org.opencontainers.image.authors="factory-prototype"

#--MODULE:security--#
#--ENDMODULE--#

#--MODULE:core--#
#--ENDMODULE--#

#--MODULE:light--#
#--ENDMODULE--#

#--MODULE:model_serve_mock--#
#--ENDMODULE--#
