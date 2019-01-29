# tfbuilder is a module for easy creation of test-format XML files.
# This file is part of tfbuilder.
#
# Copyright (C) 2018  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Constants for common test specifications."""

COVER_ERROR = "CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )"
"""Specification that __VERIFIER_error should never be reached"""

BRANCH_COVERAGE = "CHECK( init(main()), FQL(cover EDGES(@DECISIONEDGE)) )"
"""Specification that all branches should be covered (branch coverage)"""

CONDITION_COVERAGE = "CHECK( init(main()), FQL(cover EDGES(@CONDITIONEDGE)) )"
"""Specification that all condition outcomes should be covered (condition coverage)"""

STATEMENT_COVERAGE = "CHECK( init(main()), FQL(cover EDGES(@BASICBLOCKENTRY)) )"
"""Specification that all statemens should be covered (statement coverage)"""
