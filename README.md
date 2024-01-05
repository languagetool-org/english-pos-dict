# english-pos-dict

English part-of-speech and spelling dictionaries.


## To make a release

* set the version in `pom.xml` to not include `SNAPSHOT`
* `mvn clean test`
* `mvn clean deploy -P release`
* go to https://oss.sonatype.org/#stagingRepositories
* scroll to the bottom, select latest version, and click `Release`
* `git tag vx.y`
* `git push origin vx.y`