# Application information

`common_utils`
	- App contains utilities for date, email, report, transaction and security

`zrcommission`
	- App contains all the codebase which is related to commissions. Dashboard urls related to commission logic can found here.

`zrmapping`
	- App contains merchant-distributor, sub-distributor-distributor, distributor-sub distributor, sendor-benifinionary relationship mappings. 

`zrpayment`
	- App contains payment requests, mosambee payments related stuff

`zrtransaction`
	- App contains dashboard and models for transactions

`zrwallet`
	- App contains dashboard and models for wallet


### local settings
	- `local_settings.py` needs to be created in your zrcms directory to override default settings. 

### Logs
	- Logs will be created inside main directory with name zrcms.log

### Production deployment
	- To do deployment ssh to production server and follow below steps
		`cd zrupee-docker/`
		`./deploy.sh`

### Stage environement deployment process
	- Never merge anything directly into pre-master unless it is hot-fix. 
	- Merge all the changes into `pre-master` branch. Deploy it on stage environment
	- Merge `pre-master` branch once everything is working fine on stage.
